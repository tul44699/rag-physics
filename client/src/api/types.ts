export interface Textbook {
  id: number;
  title: string;
  group_name: string | null;
  page_count: number | null;
  chapter_count: number | null;
  created_at: string;
}

export interface Chapter {
  id: number;
  textbook_id: number;
  title: string;
  page_start: number;
  page_end: number | null;
}

export interface TextbookDetail extends Textbook {
  chapters: Chapter[];
}

export interface TextChunk {
  id: string;
  chapter: string | null;
  page_start: number | null;
  page_end: number | null;
  content: string;
}

export interface UserProfile {
  understanding_level?: string;
  learning_style?: string;
  course?: string;
  focus_chapters?: string[];
  chapter_minutes?: Record<string, number>;
  avg_score?: number | null;
  flashcards_generated?: number;
  study_guides_generated?: number;
  chapter_summaries_generated?: number;
  strength_areas?: string[];
  weak_areas?: string[];
  [key: string]: unknown;
}

export interface StudyEventRequest {
  event_type: string;
  chapter?: string | null;
  textbook_id?: number | null;
  minutes_spent?: number;
  score?: number | null;
}

export type Task = 'qa' | 'lookup' | 'flashcards' | 'study_guide' | 'chapter_summary';

export interface AskRequest {
  conversation_id: string;
  prompt: string;
  task: Task;
  textbook_ids: number[];
  understanding_level: string | null;
  page_start: number | null;
  page_end: number | null;
}

export interface Source {
  textbook_id: number | null;
  textbook: string;
  chapter: string | null;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  group_name: string | null;
  chunk_type: string | null;
  rerank_score: number | null;
  snippet: string;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  parsed: Record<string, unknown>[] | Record<string, unknown> | null;
}

export interface FormulaSheetResponse {
  sections: Record<string, Record<string, FormulaSheetItem[]>>; 
  chapter_order: string[];
  section_order: Record<string, string[]>;
}

export interface FormulaSheetItem {
  latex: string | null;
  plain_text: string;
  variables: string[];
  page_start: number | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  task?: string;
  parsed?: Record<string, unknown>[] | Record<string, unknown> | null;
}
