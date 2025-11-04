import { Module } from '@nestjs/common';
import { EventService } from './event.service';
import { EventController } from './event.controller';
import { EventsGateway } from './events.gateway';
import { PrismaModule } from '../prisma/prisma.module';

@Module({
  imports: [PrismaModule],
  controllers: [EventController],
  providers: [EventService, EventsGateway],
  exports: [EventService, EventsGateway],
})
export class EventModule {}