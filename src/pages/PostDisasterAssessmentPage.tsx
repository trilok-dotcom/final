import React from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { PostDisasterRoadAssessment } from '../components/ai/PostDisasterRoadAssessment';

export const PostDisasterAssessmentPage: React.FC = () => {
  return (
    <PageContainer>
      <PostDisasterRoadAssessment />
    </PageContainer>
  );
};
