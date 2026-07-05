import { useParams } from 'react-router-dom';
import RoomEditor from '../components/Editor/RoomEditor/RoomEditor';

export default function OfficeEditor() {
  const { roomKey } = useParams();
  return <RoomEditor roomKey={roomKey} />;
}
