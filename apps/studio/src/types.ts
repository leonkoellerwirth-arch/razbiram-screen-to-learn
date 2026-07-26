// types.ts — mirrors the /v1/process backend contract exactly.
// Family-specific fields are optional because a given card only carries the
// fields that apply to its family (options on choice, statement/answer on
// true-false, front/back on flashcard).

export interface Source {
  kind: string;
  policy: string;
  origin: string;
  path: string;
  capturedAt: string;
}

export interface Target {
  profile: string;
  capabilities: string[];
}

export interface DeckMeta {
  deckKey: string;
  title: { en: string };
  description: { en: string };
  level: string;
  difficulty: string;
  languages: { source: string; target: string };
  tags: string[];
}

export interface Evidence {
  evidenceId: string;
  kind: string;
  captureId: string;
  sourceRole: string;
  authority: string;
  extractor: string;
  runId: string;
}

export interface LocalisedText {
  value: { en: string };
  evidence: string[];
  confidence: number;
}

export type CardFamily =
  | "single-choice"
  | "multiple-select"
  | "true-false"
  | "flashcard";

export interface Option {
  optionId: string;
  text: string;
  isCorrect: boolean;
  evidence: string[];
}

export interface ReviewStatus {
  status: string;
  blockingReasons: string[];
  reviewedBy: string | null;
  reviewedAt: string | null;
}

export interface Rights {
  basis: string;
  licenseNotes: string | null;
  approvedForPublication: boolean;
}

export interface Card {
  draftId: string;
  cardId: string;
  sourceId: string;
  family: CardFamily;
  prompt: LocalisedText;
  review: ReviewStatus;
  rights: Rights;
  answerEvidenceTier: string;
  // choice families (single-choice, multiple-select)
  options?: Option[];
  correctOptionIds?: string[];
  // true-false only
  statement?: LocalisedText;
  answer?: boolean;
  labels?: { true: string; false: string };
  // flashcard only
  front?: LocalisedText;
  back?: LocalisedText;
}

export interface CaptureIr {
  schemaVersion: string;
  sessionId: string;
  source: Source;
  target: Target;
  deck: DeckMeta;
  evidence: Evidence[];
  cards: Card[];
}

export interface Issue {
  code: string;
  message: string;
  blocking: boolean;
  cardId?: string;
}

export interface BlockedCard {
  cardId: string;
  family: string;
  reason: string;
}

export interface ExportDeck {
  schemaId: string;
  meta: Record<string, unknown>;
  cards: unknown[];
}

/** The export shape from /v1/process.  Named ProcessExport to avoid collision
 *  with the JS `export` keyword when used as a property or local binding. */
export interface ProcessExport {
  deck: ExportDeck | null;
  blockedCardIds: string[];
  blocked: BlockedCard[];
}

export interface ProcessResponse {
  captureIr: CaptureIr;
  issues: Issue[];
  /** Raw property name in JSON is "export". */
  export: ProcessExport;
  unsupported: string[];
}
