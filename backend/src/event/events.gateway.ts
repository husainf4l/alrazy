import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayInit,
  OnGatewayConnection,
  OnGatewayDisconnect,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Injectable, Logger } from '@nestjs/common';
import { EventService } from '../event/event.service';

@Injectable()
@WebSocketGateway({
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
    transports: ['websocket', 'polling'],
  },
})
export class EventsGateway
  implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect
{
  @WebSocketServer()
  server: Server;

  private logger: Logger = new Logger('EventsGateway');
  private connectedClients = new Set<string>();

  constructor(private readonly eventService: EventService) {}

  afterInit(server: Server) {
    this.logger.log('WebSocket gateway initialized');
  }

  handleConnection(client: Socket, ...args: any[]) {
    this.logger.log(`Client connected: ${client.id}`);
    this.connectedClients.add(client.id);
    this.logger.log(`Total connected clients: ${this.connectedClients.size}`);
    
    // Send connection confirmation
    client.emit('connection', {
      message: 'Connected to events gateway',
      timestamp: new Date(),
    });
  }

  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
    this.connectedClients.delete(client.id);
    this.logger.log(`Total connected clients: ${this.connectedClients.size}`);
  }

  /**
   * Broadcast event to all connected clients
   */
  broadcastEvent(eventData: any) {
    this.server.emit('event:detected', {
      ...eventData,
      broadcastedAt: new Date(),
    });
  }

  /**
   * Broadcast to specific camera subscribers
   */
  broadcastCameraEvent(cameraId: number, eventData: any) {
    this.server.to(`camera:${cameraId}`).emit('event:detected', {
      ...eventData,
      cameraId,
      broadcastedAt: new Date(),
    });
  }

  /**
   * Broadcast lock status change
   */
  broadcastLockStatus(status: 'OPEN' | 'CLOSED', metadata?: any) {
    this.server.emit('lock:status', {
      status,
      metadata,
      timestamp: new Date(),
    });
  }

  /**
   * Handle client subscribing to specific camera
   */
  @SubscribeMessage('subscribe:camera')
  handleCameraSubscribe(client: Socket, data: { cameraId: number }) {
    const room = `camera:${data.cameraId}`;
    client.join(room);
    this.logger.log(`Client ${client.id} subscribed to ${room}`);
    
    client.emit('subscription:confirmed', {
      room,
      message: `Subscribed to camera ${data.cameraId}`,
    });
  }

  /**
   * Handle client unsubscribing from specific camera
   */
  @SubscribeMessage('unsubscribe:camera')
  handleCameraUnsubscribe(client: Socket, data: { cameraId: number }) {
    const room = `camera:${data.cameraId}`;
    client.leave(room);
    this.logger.log(`Client ${client.id} unsubscribed from ${room}`);
    
    client.emit('unsubscription:confirmed', {
      room,
      message: `Unsubscribed from camera ${data.cameraId}`,
    });
  }

  /**
   * Handle client requesting latest events
   */
  @SubscribeMessage('request:latest-events')
  async handleLatestEventsRequest(client: Socket, data?: { limit?: number }) {
    const limit = data?.limit || 10;
    const events = await this.eventService.findAll(limit);
    
    client.emit('latest:events', {
      events,
      count: events.length,
      timestamp: new Date(),
    });
  }

  /**
   * Handle unresolved events request
   */
  @SubscribeMessage('request:unresolved-events')
  async handleUnresolvedEventsRequest(client: Socket) {
    const events = await this.eventService.findUnresolved();
    
    client.emit('unresolved:events', {
      events,
      count: events.length,
      timestamp: new Date(),
    });
  }

  /**
   * Ping to keep connection alive
   */
  @SubscribeMessage('ping')
  handlePing(client: Socket): void {
    client.emit('pong', { timestamp: new Date() });
  }

  getConnectedClientsCount(): number {
    return this.connectedClients.size;
  }
}