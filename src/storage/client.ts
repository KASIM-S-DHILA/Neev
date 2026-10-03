import type { Session } from "../model";

export type Workspace = { id: string; name: string };
export type Job = {
  id: string;
  workspace_id: string;
  subject_id: string | null;
  source_version_id: string | null;
  kind: "verify_original" | "queue_fixture" | "extract_source" | "cloud_visuals" | "video_frames" | "youtube_import";
  provider?: string;
  automatic?: boolean;
  label: string;
  state:
    | "queued"
    | "running"
    | "succeeded"
    | "partial"
    | "failed"
    | "cancelled";
  stage: string;
  done: number;
  total: number;
  error: string | null;
  cancel_requested: boolean;
  attempts: number;
  failures: number;
  max_attempts: number;
  recoveries: number;
  created_at: number;
  updated_at: number;
  checkpoint: Record<string, unknown>;
  result: Record<string, unknown> | null;
};
export type QueueStatus = {
  available: boolean;
  error: string | null;
  restarts: number;
  max_active_heavy_jobs: number;
  evaluation_enabled: boolean;
};
export type WorkspaceRecord = {
  workspace: Workspace;
  revision: number;
  session: Session | null;
};
export type SourceVersion = {
  id: string;
  version: number;
  filename: string;
  sha256: string;
  size_bytes: number;
  state: "stored";
  created_at: string;
  extraction: {
    job_id: string;
    state: Job["state"];
    done: number;
    total: number;
    error: string | null;
    result: ExtractionResult | null;
  } | null;
};
export type ExtractionResult = {
  units: number;
  counts: Record<
    "text" | "needs_ocr" | "empty" | "unreadable" | "too_large" | "suspect",
    number
  >;
  warnings: number;
  text_only: boolean;
  source_sha256: string;
  youtube?: YouTubeProvenance;
};
export type YouTubeProvenance = { video_id: string; url: string; requested_language: string;
  language_code: string | null; is_generated: boolean | null; coverage: "captions_only" | "link_only";
  issue: string | null; translated: false; tracks: {language: string; language_code: string; is_generated: boolean}[] };
export type ContentUnit = {
  id: string;
  ordinal: number;
  locator:
    | {
        kind: "page";
        page: number;
        width?: number;
        height?: number;
        rotation?: number;
      }
    | { kind: "slide"; slide: number }
    | { kind: "image"; page: number }
    | { kind: "time"; start_seconds: number; end_seconds: number }
    | {
        kind: "lines";
        line_start: number;
        line_end: number;
        char_start: number;
        char_end: number;
        encoding: string;
      };
  text: string;
  text_sha256: string;
  status:
    | "text"
    | "needs_ocr"
    | "empty"
    | "unreadable"
    | "too_large"
    | "suspect";
  warning: string | null;
  engine: string;
  metadata: {
    youtube?: YouTubeProvenance;
    video?: { duration_seconds: number; container_start_seconds: number; audio_present: boolean;
      audio_start_seconds: number | null; width: number; height: number; codec: string; rotation: number; coverage: "audio_only" };
    audio?: { data_url?: string; error?: string; duration_seconds: number; sample_rate: number; channels: number };
    segments?: { start_seconds: number; end_seconds: number; text: string }[];
    speech?: { language: string | null; language_probability: number | null; model_sha256: string | null;
      provider?: "groq" | "local" | "none"; model?: string; cached?: boolean; fallback_reason?: string | null };
    native_tables?: VisualTable[];
    cloud_visuals?: {
      provider?: string;
      status: "local" | "complete" | "needs_review";
      routing: { decision: string; reasons: string[] };
      model?: string;
      error?: string;
      extraction?: {
        is_blank: boolean;
        text_lines: string[];
        tables: VisualTable[];
        equations: string[];
        diagram_nodes: string[];
        diagram_edges: { from: string; to: string; label: string }[];
        uncertainties: string[];
      };
    }[];
    assets?: {
      data_url?: string;
      caption: string;
      width: number;
      height: number;
      error?: string;
    }[];
    text_origin?: string;
    review_required?: boolean;
    ocr?: {
      language?: string;
      mean_confidence?: number | null;
      words?: { text: string; box: number[]; confidence: number }[];
    };
    image_text?: {
      picture: number;
      text: string;
      ocr: { language?: string; mean_confidence?: number | null };
    }[];
    equations?: string[];
    equation_previews?: EquationPreview[];
    visual_notes?: {
      text?: string;
      model: string;
      verified: false;
      error?: string;
    } | null;
  };
};
export type EquationPreview = {
  kind: "row" | "text" | "fraction" | "sup" | "sub" | "subsup" | "unsupported";
  text?: string;
  children?: EquationPreview[];
};
export type VisualTable = { headers: string[]; rows: string[][]; notes: string[] };
export type VisionStatus = { configured: boolean; model: string; automatic: boolean };
export type VideoFramePage = {
  version_id: string; source_sha256: string; job: Job | null; total: number; offset: number;
  frames: { id: string; seconds: number; reasons: string[]; review_required: true; ocr_pending: true;
    asset: { data_url?: string; error?: string; sha256: string; width: number; height: number; caption: string } }[];
};
export type ExtractedContent = {
  cloud_job: Job | null;
  version_id: string;
  filename: string;
  version: number;
  kind: string;
  sha256: string;
  integrity_verified: boolean;
  state: Job["state"] | "unsupported";
  error: string | null;
  total: number;
  completed: number;
  result: ExtractionResult | null;
  offset: number;
  units: ContentUnit[];
};
export type Source = {
  id: string;
  display_name: string;
  kind: string;
  versions: SourceVersion[];
};
export type FileTicket = { id: string; name: string; size: number };
export type ImportResult = {
  source_id: string;
  version_id: string;
  version: number;
  duplicate: boolean;
};
export type StorageInfo = {
  data_directory: string;
  database_path: string;
  originals_directory: string;
  max_file_bytes: number;
};
export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: { message: string; status: number } };
export type StorageBridge = {
  request: (payload: {
    action:
      | "listWorkspaces"
      | "createWorkspace"
      | "loadSession"
      | "saveSession"
      | "storageInfo"
      | "health"
      | "queueStatus"
      | "listJobs"
      | "cancelJob"
      | "retryJob"
      | "verifyOriginal"
      | "processVisuals"
      | "visionStatus"
      | "audioStatus"
      | "importYouTube"
      | "openYouTube"
      | "processAudio"
      | "processVideoFrames"
      | "readVideoFrames"
      | "processCloudVisuals"
      | "readContent"
      | "createQueueTest";
    workspaceId?: string;
    jobId?: string;
    versionId?: string;
    offset?: number;
    body?: unknown;
  }) => Promise<Result<unknown>>;
  listSources: (payload: {
    workspaceId: string;
    subjectId: string;
  }) => Promise<Result<Source[]>>;
  chooseFiles: (payload: {
    multiple: boolean;
  }) => Promise<Result<FileTicket[]>>;
  importFile: (payload: {
    workspaceId: string;
    subjectId: string;
    ticketId: string;
    sourceId?: string;
  }) => Promise<Result<ImportResult>>;
  cancelImport: (payload: { ticketId: string }) => Promise<Result<unknown>>;
  download: (payload: {
    versionId: string;
    filename: string;
  }) => Promise<Result<{ canceled: boolean }>>;
};
export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}
export function unwrap<T>(result: Result<T>): T {
  if (!result.ok) throw new ApiError(result.error.message, result.error.status);
  return result.data;
}
async function browserRequest<T>(
  route: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api" + route, {
      signal: AbortSignal.timeout(15000),
      ...options,
    });
  } catch {
    throw new ApiError(
      "The local service is unavailable. Retry the connection.",
    );
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      "The local service returned an unreadable response.",
      response.status,
    );
  }
  if (!response.ok) {
    const detail = (data as { detail?: unknown })?.detail;
    throw new ApiError(
      typeof detail === "string"
        ? detail
        : "The workspace data could not be saved.",
      response.status,
    );
  }
  return data as T;
}
async function operation<T>(
  action: Parameters<StorageBridge["request"]>[0]["action"],
  route: string,
  workspaceId?: string,
  body?: unknown,
  target?: { jobId?: string; versionId?: string; offset?: number },
): Promise<T> {
  if (window.studyLens?.storage)
    return unwrap(
      await window.studyLens.storage.request({
        action,
        workspaceId,
        body,
        ...target,
      }),
    ) as T;
  return browserRequest<T>(
    route,
    body === undefined &&
      !["cancelJob", "retryJob", "verifyOriginal", "processVisuals", "processAudio"].includes(
        action,
      )
      ? {}
      : {
          method: action === "saveSession" ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
}
export const storageClient = {
  importYouTube: async (workspaceId: string, subjectId: string, url: string, language: string, title = ""): Promise<Job> => {
    if(window.studyLens?.storage) return unwrap(await window.studyLens.storage.request({action:"importYouTube",workspaceId,body:{subjectId,url,language,title}})) as Job;
    return browserRequest<Job>(`/workspaces/${encodeURIComponent(workspaceId)}/subjects/${encodeURIComponent(subjectId)}/youtube`,
      {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url,language,title})});
  },
  openYouTube: async (url: string) => {
    if (window.studyLens?.storage) return unwrap(await window.studyLens.storage.request({action:"openYouTube",body:{url}}));
    window.open(url,"_blank","noopener,noreferrer");
  },
  videoFrames: (workspaceId: string, versionId: string, offset = 0) => operation<VideoFramePage>(
    "readVideoFrames", `/workspaces/${encodeURIComponent(workspaceId)}/source-versions/${encodeURIComponent(versionId)}/video-frames?offset=${offset}`,
    workspaceId, undefined, {versionId, offset}),
  processVideoFrames: (workspaceId: string, versionId: string) => operation<Job>(
    "processVideoFrames", `/workspaces/${encodeURIComponent(workspaceId)}/source-versions/${encodeURIComponent(versionId)}/process-video-frames`,
    workspaceId, {}, {versionId}),
  audioStatus: () => operation<{ ffmpeg: boolean; ffprobe: boolean; recognizer: boolean; model_ready: boolean; cloud_enabled: boolean; model: string }>("audioStatus", "/audio"),
  processAudio: (workspaceId: string, versionId: string) => operation<Job>("processAudio",
    "/workspaces/" + encodeURIComponent(workspaceId) + "/source-versions/" + encodeURIComponent(versionId) + "/process-audio",
    workspaceId, undefined, { versionId }),
  visionStatus: () => operation<VisionStatus>("visionStatus", "/vision"),
  processCloudVisuals: (workspaceId: string, versionId: string, ordinal?: number) =>
    operation<Job>("processCloudVisuals", "/workspaces/" + encodeURIComponent(workspaceId) +
      "/source-versions/" + encodeURIComponent(versionId) + "/cloud-visuals", workspaceId,
      { provider: "groq", ...(ordinal === undefined ? {} : { ordinal }) }, { versionId }),
  processVisuals: (workspaceId: string, versionId: string) =>
    operation<Job>(
      "processVisuals",
      "/workspaces/" +
        encodeURIComponent(workspaceId) +
        "/source-versions/" +
        encodeURIComponent(versionId) +
        "/process-visuals",
      workspaceId,
      undefined,
      { versionId },
    ),
  content: (workspaceId: string, versionId: string, offset: number) =>
    operation<ExtractedContent>(
      "readContent",
      "/workspaces/" +
        encodeURIComponent(workspaceId) +
        "/source-versions/" +
        encodeURIComponent(versionId) +
        "/content?offset=" +
        offset,
      workspaceId,
      undefined,
      { versionId, offset },
    ),
  queueStatus: () => operation<QueueStatus>("queueStatus", "/queue"),
  listJobs: (id: string) =>
    operation<Job[]>(
      "listJobs",
      "/workspaces/" + encodeURIComponent(id) + "/jobs",
      id,
    ),
  cancelJob: (workspaceId: string, jobId: string) =>
    operation<Job>(
      "cancelJob",
      "/workspaces/" +
        encodeURIComponent(workspaceId) +
        "/jobs/" +
        encodeURIComponent(jobId) +
        "/cancel",
      workspaceId,
      undefined,
      { jobId },
    ),
  retryJob: (workspaceId: string, jobId: string) =>
    operation<Job>(
      "retryJob",
      "/workspaces/" +
        encodeURIComponent(workspaceId) +
        "/jobs/" +
        encodeURIComponent(jobId) +
        "/retry",
      workspaceId,
      undefined,
      { jobId },
    ),
  verifyOriginal: (workspaceId: string, versionId: string) =>
    operation<Job>(
      "verifyOriginal",
      "/workspaces/" +
        encodeURIComponent(workspaceId) +
        "/source-versions/" +
        encodeURIComponent(versionId) +
        "/verify",
      workspaceId,
      undefined,
      { versionId },
    ),
  createQueueTest: (workspaceId: string) =>
    operation<Job>(
      "createQueueTest",
      "/workspaces/" + encodeURIComponent(workspaceId) + "/queue-test",
      workspaceId,
      {},
    ),
  listWorkspaces: () => operation<Workspace[]>("listWorkspaces", "/workspaces"),
  createWorkspace: (name: string) =>
    operation<Workspace>("createWorkspace", "/workspaces", undefined, { name }),
  loadSession: (id: string) =>
    operation<WorkspaceRecord>(
      "loadSession",
      "/workspaces/" + encodeURIComponent(id) + "/session",
      id,
    ),
  saveSession: (id: string, session: Session, revision: number) =>
    operation<{ revision: number }>(
      "saveSession",
      "/workspaces/" + encodeURIComponent(id) + "/session",
      id,
      { base_revision: revision, session },
    ),
  storageInfo: () => operation<StorageInfo>("storageInfo", "/storage"),
  listSources: (workspaceId: string, subjectId: string) =>
    window.studyLens?.storage
      ? window.studyLens.storage
          .listSources({ workspaceId, subjectId })
          .then(unwrap)
      : browserRequest<Source[]>(
          "/workspaces/" +
            encodeURIComponent(workspaceId) +
            "/subjects/" +
            encodeURIComponent(subjectId) +
            "/sources",
        ),
  async importBrowserFile(
    workspaceId: string,
    subjectId: string,
    file: File,
    signal: AbortSignal,
    sourceId?: string,
  ) {
    const query = new URLSearchParams({ filename: file.name });
    if (sourceId) query.set("source_id", sourceId);
    return browserRequest<ImportResult>(
      "/workspaces/" +
        encodeURIComponent(workspaceId) +
        "/subjects/" +
        encodeURIComponent(subjectId) +
        "/sources?" +
        query,
      {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
        signal,
      },
    );
  },
};
