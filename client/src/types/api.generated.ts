/* Thin application aliases over src/types/openapi.d.ts, generated from FastAPI. */
import type { components } from './openapi';


export type User = components['schemas']['UserRead'];
export type UserRole = User['role'];
export type LoginResponse = components['schemas']['LoginResponse'];
export type ContentTag = components['schemas']['ContentTagRead'];
export type Level2Category = components['schemas']['Level2CategoryRead'];
export type BusinessLabel = components['schemas']['BusinessLabelRead'];
export type AnalysisRun = components['schemas']['AnalysisRunRead'];
export type AuditLog = components['schemas']['AuditLogRead'];

type GeneratedTag = components['schemas']['TagRead'];
export type Tag = Omit<GeneratedTag, 'parentId'> & { parentId: string | null };

type GeneratedImage = components['schemas']['ImageRead'];
export type ImageItem = Omit<GeneratedImage, 'tags'> & { tags: Tag[] };

type GeneratedImageDetail = components['schemas']['ImageDetailRead'];
export type ImageDetail = Omit<
  GeneratedImageDetail,
  | 'tags'
  | 'relatedImages'
  | 'contentTags'
  | 'level2Categories'
  | 'businessLabels'
  | 'analysisRuns'
> & {
  tags: Tag[];
  relatedImages: ImageItem[];
  contentTags: ContentTag[];
  level2Categories: Level2Category[];
  businessLabels: BusinessLabel[];
  analysisRuns: AnalysisRun[];
};

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}
