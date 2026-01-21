export interface NotebookResponse {
  id: number
  name: string
  description: string
  archived: boolean
  created: string
  updated: string
  source_count: number
  note_count: number
}

export interface NoteResponse {
  id: number
  title: string | null
  content: string | null
  note_type: string | null
  created: string
  updated: string
}

export interface SourceListResponse {
  id: number
  title: string | null
  topics?: string[]                  // Make optional to match Python API
  asset: {
    file_path?: string
    url?: string
  } | null
  embedded: boolean
  embedded_chunks: number            // ADD: From Python API
  insights_count: number
  created: string
  updated: string
  file_available?: boolean
  // ADD: Async processing fields from Python API
  command_id?: string
  status?: string
  processing_info?: Record<string, unknown>
}

export interface SourceDetailResponse extends SourceListResponse {
  full_text: string
  notebooks?: number[]  // List of notebook IDs this source is linked to
}

export type SourceResponse = SourceDetailResponse

export interface SourceStatusResponse {
  status?: string
  message: string
  processing_info?: Record<string, unknown>
  command_id?: string
}

export interface SettingsResponse {
  default_content_processing_engine_doc?: string
  default_content_processing_engine_url?: string
  default_embedding_option?: string
  auto_delete_files?: string
  youtube_preferred_languages?: string[]
}

export interface CreateNotebookRequest {
  name: string
  description?: string
}

export interface UpdateNotebookRequest {
  name?: string
  description?: string
  archived?: boolean
}

export interface CreateNoteRequest {
  title?: string
  content: string
  note_type?: string
  notebook_id?: number
}

export interface CreateSourceRequest {
  // Backward compatibility: support old single notebook_id
  notebook_id?: number
  // New multi-notebook support
  notebooks?: number[]
  // Required fields
  type: 'link' | 'upload' | 'text'
  url?: string
  file_path?: string
  content?: string
  title?: string
  transformations?: string[]
  embed?: boolean
  delete_source?: boolean
  // New async processing support
  async_processing?: boolean
}

export interface UpdateNoteRequest {
  title?: string
  content?: string
  note_type?: string
}

export interface UpdateSourceRequest {
  title?: string
  type?: 'link' | 'upload' | 'text'
  url?: string
  content?: string
}

export interface APIError {
  detail: string
}

// Source Chat Types
// Base session interface with common fields
export interface BaseChatSession {
  id: number
  title: string
  created: string
  updated: string
  message_count?: number
  model_override?: string | null
}

export interface SourceChatSession extends BaseChatSession {
  source_id: number
  model_override?: string
}

export interface SourceChatMessage {
  id: number
  type: 'human' | 'ai'
  content: string
  timestamp?: string
}

export interface SourceChatContextIndicator {
  sources: number[]
  insights: number[]
  notes: number[]
}

export interface SourceChatSessionWithMessages extends SourceChatSession {
  messages: SourceChatMessage[]
  context_indicators?: SourceChatContextIndicator
}

export interface CreateSourceChatSessionRequest {
  source_id: number
  title?: string
  model_override?: string
}

export interface UpdateSourceChatSessionRequest {
  title?: string
  model_override?: string
}

export interface SendMessageRequest {
  message: string
  model_override?: string
}

export interface SourceChatStreamEvent {
  type: 'user_message' | 'ai_message' | 'context_indicators' | 'complete' | 'error'
  content?: string
  data?: unknown
  message?: string
  timestamp?: string
}

// Notebook Chat Types
export interface NotebookChatSession extends BaseChatSession {
  notebook_id: number
}

export interface NotebookChatMessage {
  id: number
  type: 'human' | 'ai'
  content: string
  timestamp?: string
}

export interface NotebookChatSessionWithMessages extends NotebookChatSession {
  messages: NotebookChatMessage[]
}

export interface CreateNotebookChatSessionRequest {
  notebook_id: number
  title?: string
  model_override?: string
}

export interface UpdateNotebookChatSessionRequest {
  title?: string
  model_override?: string | null
}

export interface SendNotebookChatMessageRequest {
  session_id: number
  message: string
  context: {
    sources: Array<Record<string, unknown>>
    notes: Array<Record<string, unknown>>
  }
  model_override?: string
}

export interface BuildContextRequest {
  notebook_id: number
  context_config: {
    sources: Record<number, string>
    notes: Record<number, string>
  }
}

export interface BuildContextResponse {
  context: {
    sources: Array<Record<string, unknown>>
    notes: Array<Record<string, unknown>>
  }
  token_count: number
  char_count: number
}
