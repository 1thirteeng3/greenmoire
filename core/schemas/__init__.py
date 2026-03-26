from core.schemas.cognitive import ExecutionPlan, IntentTier, ParsedIntent
from core.schemas.events import BaseEvent, EventHeader
from core.schemas.ingestion import (
    ChunkedContent,
    ContentChunkedEvent,
    ContentExtractedEvent,
    ContentVectorizedEvent,
    IngestionRequest,
    IngestionRequestedEvent,
    IngestionTask,
    IngestionTaskStatus,
    IngestionSourceType,
    VectorizedContent,
)
from core.schemas.memory import BaseMemoryEntity, EpisodicMemory, ErrorMemory, MemoryMetadata, SemanticMemory
from core.schemas.sync import ObsidianSyncState, SyncJobStatus, SyncLockStatus
from core.schemas.tools import (
    BaseToolInput,
    FetchUrlToolInput,
    ToolCallEnvelope,
    ToolName,
    UpsertMemoryToolInput,
    WebSearchToolInput,
    WriteNoteToolInput,
)

# Backward-compat aliases for older imports.
SearchMemoryToolInput = WebSearchToolInput
UpsertSemanticMemoryToolInput = UpsertMemoryToolInput
ObsidianSyncStatus = SyncJobStatus

__all__ = [
    "BaseEvent",
    "EventHeader",
    "MemoryMetadata",
    "BaseMemoryEntity",
    "SemanticMemory",
    "EpisodicMemory",
    "ErrorMemory",
    "IntentTier",
    "ParsedIntent",
    "ExecutionPlan",
    "IngestionSourceType",
    "IngestionTaskStatus",
    "IngestionTask",
    "IngestionRequest",
    "ChunkedContent",
    "VectorizedContent",
    "IngestionRequestedEvent",
    "ContentExtractedEvent",
    "ContentChunkedEvent",
    "ContentVectorizedEvent",
    "ToolName",
    "BaseToolInput",
    "WebSearchToolInput",
    "FetchUrlToolInput",
    "WriteNoteToolInput",
    "UpsertMemoryToolInput",
    "SearchMemoryToolInput",
    "UpsertSemanticMemoryToolInput",
    "ToolCallEnvelope",
    "SyncLockStatus",
    "SyncJobStatus",
    "ObsidianSyncStatus",
    "ObsidianSyncState",
]
