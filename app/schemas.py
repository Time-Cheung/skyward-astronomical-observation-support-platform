from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import MAX_CALCULATION_DAYS, SITE_TIMEZONE_NAME


class ConstraintSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The planning UI deliberately caps solar altitude at -15 degrees. This
    # keeps the user-selectable operating regime at astronomical dusk or darker.
    sun_max_altitude_deg: Optional[float] = Field(default=None, ge=-90, le=-15)
    moon_min_separation_deg: Optional[float] = Field(default=None, ge=0, le=180)
    target_min_zenith_deg: Optional[float] = Field(default=None, ge=0, le=90)
    target_max_zenith_deg: Optional[float] = Field(default=None, ge=0, le=90)
    minimum_window_seconds: Optional[int] = Field(default=None, ge=0, le=2_592_000)

    @model_validator(mode="after")
    def validate_zenith_range(self) -> "ConstraintSet":
        if (
            self.target_min_zenith_deg is not None
            and self.target_max_zenith_deg is not None
            and self.target_min_zenith_deg > self.target_max_zenith_deg
        ):
            raise ValueError("target_min_zenith_deg must be <= target_max_zenith_deg")
        return self

    @property
    def minimum_duration(self) -> int:
        return int(self.minimum_window_seconds or 0)

    def enabled_labels(self) -> List[str]:
        labels = []
        if self.sun_max_altitude_deg is not None:
            labels.append("sun_altitude")
        if self.moon_min_separation_deg is not None:
            labels.append("moon_separation")
        if self.target_min_zenith_deg is not None:
            labels.append("target_min_zenith")
        if self.target_max_zenith_deg is not None:
            labels.append("target_max_zenith")
        if self.minimum_duration:
            labels.append("minimum_window")
        return labels


class WindowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A source index, an all-catalogue request, or a custom J2000 circular
    # region is accepted. Exactly one target selection is required.
    source_index: Optional[int] = Field(default=None, ge=0)
    source_key: Optional[str] = Field(default=None, min_length=1, max_length=256)
    catalog_token: Optional[str] = None
    catalog_tokens: Optional[str] = None
    nominal_radius_deg: Optional[float] = Field(default=None, gt=0, le=90)
    all_sources: bool = False
    region_ra_deg: Optional[float] = Field(default=None, ge=0, lt=360)
    region_dec_deg: Optional[float] = Field(default=None, ge=-90, le=90)
    region_radius_deg: Optional[float] = Field(default=None, gt=0, le=90)
    region_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    start_time: datetime
    end_time: datetime
    constraints: ConstraintSet = Field(default_factory=ConstraintSet)

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=ZoneInfo(SITE_TIMEZONE_NAME))
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "WindowRequest":
        self.start_time = self._as_aware(self.start_time)
        self.end_time = self._as_aware(self.end_time)
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if (self.end_time - self.start_time).total_seconds() > MAX_CALCULATION_DAYS * 86400:
            raise ValueError(f"time range cannot exceed {MAX_CALCULATION_DAYS} days")
        region_values = (self.region_ra_deg, self.region_dec_deg, self.region_radius_deg)
        region_requested = any(value is not None for value in region_values)
        if region_requested and not all(value is not None for value in region_values):
            raise ValueError("region_ra_deg, region_dec_deg and region_radius_deg must be supplied together")
        if self.region_name is not None and not region_requested:
            raise ValueError("region_name may only be supplied with a custom region")
        target_count = int(self.source_index is not None or self.source_key is not None) + int(self.all_sources) + int(region_requested)
        if target_count != 1:
            raise ValueError("select exactly one of source_index, all_sources or a custom region")
        return self

    @property
    def start_utc(self) -> datetime:
        return self.start_time.astimezone(timezone.utc)

    @property
    def end_utc(self) -> datetime:
        return self.end_time.astimezone(timezone.utc)


class AlternativeWindowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1, max_length=256)
    catalog_token: Optional[str] = None
    catalog_tokens: Optional[str] = None
    alternative_catalog_token: Optional[str] = Field(default=None, min_length=1, max_length=256)
    nominal_radius_deg: Optional[float] = Field(default=None, gt=0, le=90)
    search_start: datetime
    search_end: datetime
    target_window_start: datetime
    target_window_end: datetime
    constraints: ConstraintSet = Field(default_factory=ConstraintSet)
    max_alternatives: int = Field(default=3, ge=1, le=3)
    coarse_step_seconds: int = Field(default=900, ge=600, le=1800)
    shortlist_limit: int = Field(default=8, ge=1, le=12)

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=ZoneInfo(SITE_TIMEZONE_NAME))
        return value

    @model_validator(mode="after")
    def validate_ranges(self) -> "AlternativeWindowRequest":
        for field in ("search_start", "search_end", "target_window_start", "target_window_end"):
            setattr(self, field, self._as_aware(getattr(self, field)))
        if self.search_end <= self.search_start:
            raise ValueError("search_end must be later than search_start")
        if (self.search_end - self.search_start).total_seconds() > MAX_CALCULATION_DAYS * 86400:
            raise ValueError(f"search range cannot exceed {MAX_CALCULATION_DAYS} days")
        if self.target_window_end <= self.target_window_start:
            raise ValueError("target_window_end must be later than target_window_start")
        if self.target_window_start < self.search_start or self.target_window_end > self.search_end:
            raise ValueError("target window must lie inside the search range")
        return self

    @property
    def search_start_utc(self) -> datetime:
        return self.search_start.astimezone(timezone.utc)

    @property
    def search_end_utc(self) -> datetime:
        return self.search_end.astimezone(timezone.utc)

    @property
    def target_start_utc(self) -> datetime:
        return self.target_window_start.astimezone(timezone.utc)

    @property
    def target_end_utc(self) -> datetime:
        return self.target_window_end.astimezone(timezone.utc)


class SkyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at_time: Optional[datetime] = None
    selected_source_index: Optional[int] = Field(default=None, ge=0)
    constraints: ConstraintSet = Field(default_factory=ConstraintSet)

    @model_validator(mode="after")
    def normalize_time(self) -> "SkyRequest":
        if self.at_time is None:
            self.at_time = datetime.now(timezone.utc)
        elif self.at_time.tzinfo is None:
            self.at_time = self.at_time.replace(tzinfo=ZoneInfo(SITE_TIMEZONE_NAME))
        return self

    @property
    def at_utc(self) -> datetime:
        assert self.at_time is not None
        return self.at_time.astimezone(timezone.utc)
