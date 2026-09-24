import type {
  MeetingDeleteResponse,
  MeetingDetail,
  MeetingListResponse,
  MeetingNotesResponse,
  MeetingSpeakersResponse,
  MeetingStatusResponse,
  MeetingTranscriptResponse,
  MeetingUploadResponse,
  TranscriptSegmentUpdateResponse,
} from "../types";


export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000";


export class ApiError extends Error {
  status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);
    this.status = status;
  }
}


async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    options,
  );

  if (!response.ok) {
    let message =
      `Request failed with status ${response.status}.`;

    try {
      const data =
        await response.json();

      if (
        typeof data?.detail ===
        "string"
      ) {
        message =
          data.detail;
      }
    } catch {
      // Keep generic fallback message.
    }

    throw new ApiError(
      message,
      response.status,
    );
  }

  return response.json() as Promise<T>;
}


export function getMeetingMediaUrl(
  meetingId: number,
) {
  return (
    `${API_BASE_URL}` +
    `/api/meetings/${meetingId}/media`
  );
}


export function getMeetingExportUrl(
  meetingId: number,
  format: "txt" | "md" | "pdf",
) {
  const params =
    new URLSearchParams({
      format,
    });

  return (
    `${API_BASE_URL}` +
    `/api/meetings/${meetingId}/export?${params.toString()}`
  );
}


export function getMeetings() {
  return request<MeetingListResponse>(
    "/api/meetings",
  );
}


export function getMeeting(
  meetingId: number,
) {
  return request<MeetingDetail>(
    `/api/meetings/${meetingId}`,
  );
}


export function getMeetingStatus(
  meetingId: number,
) {
  return request<MeetingStatusResponse>(
    `/api/meetings/${meetingId}/status`,
  );
}


export function getTranscript(
  meetingId: number,
) {
  return request<MeetingTranscriptResponse>(
    `/api/meetings/${meetingId}/transcript`,
  );
}


export function getSpeakers(
  meetingId: number,
) {
  return request<MeetingSpeakersResponse>(
    `/api/meetings/${meetingId}/speakers`,
  );
}


export function getMeetingNotes(
  meetingId: number,
) {
  return request<MeetingNotesResponse>(
    `/api/meetings/${meetingId}/notes`,
  );
}


export async function uploadMeeting(
  file: File,
  title?: string,
) {
  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

  if (title?.trim()) {
    formData.append(
      "title",
      title.trim(),
    );
  }

  return request<MeetingUploadResponse>(
    "/api/meetings/upload",
    {
      method: "POST",
      body: formData,
    },
  );
}


export function processMeetingAudio(
  meetingId: number,
) {
  return request(
    `/api/meetings/${meetingId}/process-audio`,
    {
      method: "POST",
    },
  );
}


export function transcribeMeeting(
  meetingId: number,
) {
  return request(
    `/api/meetings/${meetingId}/transcribe`,
    {
      method: "POST",
    },
  );
}


export function diarizeMeeting(
  meetingId: number,
) {
  return request(
    `/api/meetings/${meetingId}/diarize`,
    {
      method: "POST",
    },
  );
}


export function analyzeMeeting(
  meetingId: number,
) {
  return request(
    `/api/meetings/${meetingId}/analyze`,
    {
      method: "POST",
    },
  );
}


export function deleteMeeting(
  meetingId: number,
) {
  return request<MeetingDeleteResponse>(
    `/api/meetings/${meetingId}`,
    {
      method: "DELETE",
    },
  );
}


export function updateSpeaker(
  speakerId: number,
  displayName: string,
) {
  return request(
    `/api/speakers/${speakerId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        display_name:
          displayName,
      }),
    },
  );
}


export function updateTranscriptSegment(
  segmentId: number,
  text: string,
) {
  return request<TranscriptSegmentUpdateResponse>(
    `/api/transcript-segments/${segmentId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        text,
      }),
    },
  );
}
