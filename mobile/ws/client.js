import { WS_URL } from '../config';
import { getToken } from '../auth/session';

export async function connectToChannel(canal, { onMessage, onError } = {}) {
  const token = await getToken();
  if (!token) {
    return () => {};
  }

  const socket = new WebSocket(`${WS_URL}/ws/${canal}?token=${token}`);

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onMessage) onMessage(data);
    } catch (err) {
      // frame no era JSON válido, se ignora
    }
  };

  socket.onerror = (event) => {
    if (onError) onError(event);
  };

  return () => {
    socket.close();
  };
}
