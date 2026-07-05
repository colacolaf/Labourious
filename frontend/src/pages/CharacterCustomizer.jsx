import { useParams } from 'react-router-dom';
import AppearanceEditor from '../components/Editor/CharacterEditor/AppearanceEditor';

// No :agentId param = editing the current user's own avatar.
export default function CharacterCustomizer() {
  const { agentId } = useParams();
  return <AppearanceEditor agentId={agentId ? Number(agentId) : undefined} />;
}
