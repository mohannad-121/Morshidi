import type {AdaptiveCourseResponse} from '@/lib/api/student-types';
import {DifficultyDots} from '@/components/ui/DesignSystem';
export function CourseDifficulty({course,locale='ar'}:{course:AdaptiveCourseResponse['courses'][number]|undefined;locale?:'ar'|'en'}){if(!course)return null;return <DifficultyDots level={course.personalized.level} low={course.personalized.confidence==='LOW'} locale={locale}/>;}
