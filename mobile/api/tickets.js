import { request } from './client';

export function getTickets({ pagado } = {}) {
  const query = pagado === undefined ? '' : `?pagado=${pagado}`;
  return request(`/tickets${query}`);
}

export function getTicket(ticketId) {
  return request(`/tickets/${ticketId}`);
}
