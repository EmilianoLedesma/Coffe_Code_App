import { WS_URL } from '../config';
import { getToken } from '../auth/session';

export async function connectToChannel(canal, { onMessage, onError, onClose } = {}) {
  try {
    const token = await getToken();
    if (!token) {
      return () => {};
    }

    const socket = new WebSocket(`${WS_URL}/ws/${canal}?token=${token}`);

    socket.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (err) {
        // frame no era JSON válido, se ignora
        return;
      }
      if (onMessage) onMessage(data);
    };

    socket.onerror = (event) => {
      if (onError) onError(event);
    };

    socket.onclose = () => {
      if (onClose) onClose();
    };

    return () => {
      socket.onclose = null;
      socket.close();
    };
  } catch (err) {
    return () => {};
  }
}
