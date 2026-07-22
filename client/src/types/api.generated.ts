/* Thin application aliases over src/types/openapi.d.ts, generated from FastAPI. */
import type { components } from './openapi';


export type User = components['schemas']['UserRead'];
export type UserRole = User['role'];
export type LoginResponse = components['schemas']['LoginResponse'];
export type AnalysisRun = components['schemas']['AnalysisRunRead'];
export type ImageSemanticProfile = components['schemas']['SemanticProfileRead'];
export type AuditLog = components['schemas']['AuditLogRead'];
export type AssetSearchPhraseSuggestion =
  components['schemas']['AssetSearchPhraseSuggestion'];
export type ImageTitleResolution = components['schemas']['ImageTitleResolution'];

type GeneratedTag = components['schemas']['TagRead'];
export type Tag = Omit<GeneratedTag, 'parentId'> & { parentId: string | null };

type GeneratedImage = components['schemas']['ImageRead'];
export type ImageItem = GeneratedImage;

type GeneratedImageDetail = components['schemas']['ImageDetailRead'];
export type ImageDetail = Omit<
  GeneratedImageDetail,
  | 'relatedImages'
  | 'analysisRuns'
> & {
  relatedImages: ImageItem[];
  analysisRuns: AnalysisRun[];
};

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}
