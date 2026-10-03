from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, ForeignKeyConstraint, Integer, MetaData, String, Table, Text, UniqueConstraint

metadata = MetaData()


class CloudVisualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ordinal: int | None = Field(default=None, ge=1, le=10000)
    provider: Literal["groq"] = "groq"

workspaces = Table("workspaces", metadata,
    Column("id", String(200), primary_key=True),
    Column("name", String(60), nullable=False),
    Column("name_key", String(120), nullable=False, unique=True),
    Column("revision", Integer, nullable=False, default=0),
    Column("created_at", String(40), nullable=False))
subjects = Table("subjects", metadata,
    Column("workspace_id", String(200), ForeignKey("workspaces.id", ondelete="RESTRICT"), primary_key=True),
    Column("id", String(200), primary_key=True),
    Column("name", String(60), nullable=False),
    Column("name_key", String(120), nullable=False),
    Column("icon", String(20), nullable=False),
    Column("demo", Boolean, nullable=False),
    Column("position", Integer, nullable=False),
    UniqueConstraint("workspace_id", "name_key"))
topics = Table("topics", metadata,
    Column("workspace_id", String(200), primary_key=True),
    Column("subject_id", String(200), primary_key=True),
    Column("id", String(200), primary_key=True),
    Column("title", String(100), nullable=False),
    Column("title_key", String(200), nullable=False),
    Column("description", Text, nullable=False),
    Column("unit", String(80), nullable=False),
    Column("read", Boolean, nullable=False),
    Column("read_minutes", Integer),
    Column("lesson", String(30)),
    Column("position", Integer, nullable=False),
    ForeignKeyConstraint(["workspace_id", "subject_id"], ["subjects.workspace_id", "subjects.id"], ondelete="CASCADE"),
    UniqueConstraint("workspace_id", "subject_id", "title_key"))
sessions = Table("workspace_sessions", metadata,
    Column("workspace_id", String(200), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
    Column("layout_json", Text, nullable=False))
sources = Table("sources", metadata,
    Column("id", String(36), primary_key=True),
    Column("workspace_id", String(200), nullable=False),
    Column("subject_id", String(200), nullable=False),
    Column("display_name", String(255), nullable=False),
    Column("name_key", String(510), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("next_version", Integer, nullable=False, default=1),
    Column("created_at", String(40), nullable=False),
    ForeignKeyConstraint(["workspace_id", "subject_id"], ["subjects.workspace_id", "subjects.id"], ondelete="RESTRICT"),
    UniqueConstraint("workspace_id", "subject_id", "name_key"))
source_versions = Table("source_versions", metadata,
    Column("id", String(36), primary_key=True),
    Column("source_id", String(36), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True),
    Column("version", Integer, nullable=False),
    Column("filename", String(255), nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("relative_path", String(100), nullable=False),
    Column("state", String(20), nullable=False),
    Column("created_at", String(40), nullable=False),
    UniqueConstraint("source_id", "version"),
    UniqueConstraint("source_id", "sha256"))

jobs = Table("jobs", metadata,
    Column("id", String(36), primary_key=True),
    Column("workspace_id", String(200), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False),
    Column("subject_id", String(200)),
    Column("source_version_id", String(36), ForeignKey("source_versions.id", ondelete="RESTRICT")),
    Column("kind", String(30), nullable=False),
    Column("label", String(255), nullable=False),
    Column("state", String(20), nullable=False),
    Column("stage", String(80), nullable=False),
    Column("done", Integer, nullable=False),
    Column("total", Integer, nullable=False),
    Column("checkpoint_json", Text, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("result_json", Text),
    Column("error", String(1000)),
    Column("cancel_requested", Boolean, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("failures", Integer, nullable=False),
    Column("max_attempts", Integer, nullable=False),
    Column("recoveries", Integer, nullable=False),
    Column("owner", String(36)),
    Column("available_at", Float, nullable=False),
    Column("created_at", Float, nullable=False),
    Column("updated_at", Float, nullable=False),
    ForeignKeyConstraint(["workspace_id", "subject_id"], ["subjects.workspace_id", "subjects.id"], ondelete="RESTRICT"),
    UniqueConstraint("kind", "source_version_id"),
    CheckConstraint("state IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')", name="job_state"))

content_units = Table("content_units", metadata,
    Column("id", String(36), primary_key=True),
    Column("source_version_id", String(36), ForeignKey("source_versions.id", ondelete="RESTRICT"), nullable=False),
    Column("job_id", String(36), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("locator_json", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("text_sha256", String(64), nullable=False),
    Column("status", String(20), nullable=False),
    Column("warning", String(1000)),
    Column("engine", String(80), nullable=False),
    Column("metadata_json", Text, nullable=False, server_default="{}"),
    UniqueConstraint("source_version_id", "ordinal"),
    CheckConstraint("status IN ('text', 'needs_ocr', 'empty', 'unreadable', 'too_large', 'suspect')", name="content_status"))

youtube_media_links = Table("youtube_media_links", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("youtube_source_id", String(36), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
    Column("caption_version_id", String(36), ForeignKey("source_versions.id", ondelete="RESTRICT"), nullable=False),
    Column("media_version_id", String(36), ForeignKey("source_versions.id", ondelete="RESTRICT")),
    Column("youtube_start_seconds", Float, nullable=False),
    Column("created_at", String(40), nullable=False),
    CheckConstraint("youtube_start_seconds >= 0 AND youtube_start_seconds <= 14400", name="youtube_media_offset"))

Identifier = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9_-]+$")]
Name = Annotated[str, Field(min_length=1, max_length=60)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class YouTubeImport(StrictModel):
    url: Annotated[str, Field(min_length=1, max_length=2048)]
    language: Annotated[str, Field(pattern=r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})?$")] = "en"
    title: Annotated[str, Field(max_length=200)] = ""


class YouTubeMediaLink(StrictModel):
    media_version_id: Identifier
    youtube_start_seconds: Annotated[float, Field(ge=0, le=14400)] = 0


class TopicInput(StrictModel):
    id: Identifier
    title: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(max_length=500)]
    unit: Annotated[str, Field(min_length=1, max_length=80)]
    read: bool
    readMinutes: Annotated[int | None, Field(ge=0, le=10000)] = None
    lesson: Literal["conditional"] | None = None


class SubjectInput(StrictModel):
    id: Identifier
    name: Name
    icon: Literal["probability", "algebra", "code", "book"]
    demo: bool
    topics: Annotated[list[TopicInput], Field(max_length=300)]


class TabInput(StrictModel):
    id: Identifier
    view: Literal["workspace", "topics", "learn", "ask", "practice", "materials", "today", "settings"]
    draft: Annotated[str, Field(max_length=20000)]
    subjectId: Identifier | None = None
    topicId: Identifier | None = None


class SessionInput(StrictModel):
    version: Literal[1]
    tabs: Annotated[list[TabInput], Field(min_length=1, max_length=12)]
    activeTabId: Identifier
    subjects: Annotated[list[SubjectInput], Field(max_length=100)]
    sidebarCollapsed: bool

    @model_validator(mode="after")
    def references(self):
        by_id = {subject.id: subject for subject in self.subjects}
        if len(by_id) != len(self.subjects):
            raise ValueError("Duplicate subject identifier")
        names = [subject.name.strip().casefold() for subject in self.subjects]
        if any(not name for name in names) or len(set(names)) != len(names):
            raise ValueError("Subject names must be non-empty and unique")
        for subject in self.subjects:
            ids = [topic.id for topic in subject.topics]
            names = [topic.title.strip().casefold() for topic in subject.topics]
            if len(set(ids)) != len(ids) or len(set(names)) != len(names) or any(not name for name in names):
                raise ValueError("Topic identifiers and titles must be unique in their subject")
        tab_ids = [tab.id for tab in self.tabs]
        if len(set(tab_ids)) != len(tab_ids) or self.activeTabId not in tab_ids:
            raise ValueError("Invalid active tab or duplicate tab identifier")
        for tab in self.tabs:
            subject = by_id.get(tab.subjectId)
            if tab.subjectId is not None and subject is None:
                raise ValueError("Tab refers to a missing subject")
            if tab.topicId is not None and (subject is None or not any(topic.id == tab.topicId for topic in subject.topics)):
                raise ValueError("Tab refers to a missing topic")
            if tab.view not in ("workspace", "today", "settings") and subject is None:
                raise ValueError("This view requires a subject")
            if tab.view == "learn" and tab.topicId is None:
                raise ValueError("Reading requires a topic")
        return self


class SaveSession(StrictModel):
    base_revision: Annotated[int, Field(ge=0)]
    session: SessionInput


class CreateWorkspace(StrictModel):
    name: Name


class QueueFixture(StrictModel):
    steps: Annotated[int, Field(ge=1, le=200)] = 40
    delay_ms: Annotated[int, Field(ge=10, le=500)] = 250
    cpu_ms: Annotated[int, Field(ge=0, le=100)] = 0
    fail_until: Annotated[int, Field(ge=0, le=3)] = 0
    permanent_failure: bool = False
