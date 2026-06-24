import { useParams } from 'react-router-dom';
import ImageBrowser from '../ImageHome/ImageHome';

const TagExplorePage = () => {
  const { tagId } = useParams<{ tagId: string }>();
  return <ImageBrowser parentTagId={tagId} />;
};

export default TagExplorePage;
