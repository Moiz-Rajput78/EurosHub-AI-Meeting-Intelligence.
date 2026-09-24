export type MeetingStatus =
  | "UPLOADED"
  | "PROCESSING_AUDIO"
  | "TRANSCRIBING"
  | "DIARIZING"
  | "GENERATING_NOTES"
  | "COMPLETED"
  | "FAILED";


export interface MeetingListItem {
  id: number;
  title: string;
  original_filename: string;
  status: MeetingStatus;
  duration: number | null;
  language: string | null;
  transcript_segment_count: number;
  speaker_count: number;
  created_at: string;
  updated_at: string;
}


export interface MeetingListResponse {
  count: number;
  meetings: MeetingListItem[];
}


export interface MeetingDetail {
  id: number;
  title: string;
  original_filename: string;
  stored_filename: string | null;
  status: MeetingStatus;
  duration: number | null;
  language: string | null;
  transcript_segment_count: number;
  speaker_count: number;
  has_transcript: boolean;
  has_speakers: boolean;
  has_notes: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}


export interface MeetingStatusResponse {
  meeting_id: number;
  status: MeetingStatus;
  error_message: string | null;
  has_transcript: boolean;
  has_speakers: boolean;
  has_notes: boolean;
  transcript_segment_count: number;
  message: string;
}


export interface MeetingUploadResponse {
  id: number;
  title: string;
  original_filename: string;
  stored_filename: string | null;
  status: MeetingStatus;
  created_at: string;
  message: string;
}


export interface TranscriptSegment {
  id: number;
  start_time: number;
  end_time: number;
  original_text: string;
  edited_text: string | null;
  speaker_id: number | null;
  speaker_label: string | null;
  speaker_display_name: string | null;
}


export interface MeetingTranscriptResponse {
  meeting_id: number;
  title: string;
  language: string | null;
  duration: number | null;
  segment_count: number;
  segments: TranscriptSegment[];
}


export interface Speaker {
  id: number;
  speaker_label: string;
  display_name: string | null;
}


export interface MeetingSpeakersResponse {
  meeting_id: number;
  speaker_count: number;
  speakers: Speaker[];
}


export interface Decision {
  id: number;
  decision: string;
  evidence: string;
}


export interface ActionItem {
  id: number;
  task: string;
  responsible_person: string | null;
  deadline: string | null;
  priority: string;
  topic: string | null;
  evidence: string;
}


export interface ImportantDate {
  date_or_time: string;
  description: string;
  evidence: string;
}


export interface OpenIssue {
  id: number;
  issue: string;
  evidence: string;
}


export interface QuestionItem {
  question: string;
  evidence: string;
}


export interface RequirementItem {
  id: number;
  requirement: string;
  evidence: string;
}


export interface AnnouncementItem {
  announcement: string;
  evidence: string;
}


export interface MeetingNotesResponse {
  meeting_id: number;
  title: string;
  summary: string;
  key_discussion_points: string[];
  decisions: Decision[];
  action_items: ActionItem[];
  important_dates: ImportantDate[];
  open_issues: OpenIssue[];
  unanswered_questions: QuestionItem[];
  requirements: RequirementItem[];
  announcements: AnnouncementItem[];
  topics: string[];
  model_name: string;
  created_at: string;
  updated_at: string;
}


export interface MeetingDeleteResponse {
  meeting_id: number;
  deleted: boolean;
  message: string;
}


export interface TranscriptSegmentUpdateResponse {
  id: number;
  meeting_id: number;
  start_time: number;
  end_time: number;
  original_text: string;
  edited_text: string;
  speaker_id: number | null;
  notes_invalidated: boolean;
  message: string;
}