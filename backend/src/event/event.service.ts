import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateEventDto } from './dto/event.dto';
import { EventType, Event } from '@prisma/client';

@Injectable()
export class EventService {
  constructor(private readonly prisma: PrismaService) {}

  async create(createEventDto: CreateEventDto): Promise<Event> {
    // Verify camera exists
    const camera = await this.prisma.camera.findUnique({
      where: { id: createEventDto.cameraId }
    });

    if (!camera) {
      throw new NotFoundException(`Camera with ID ${createEventDto.cameraId} not found`);
    }

    // Determine event type based on person count
    let eventType: EventType = EventType.PERSON_DETECTED;
    if (createEventDto.personCount > 1) {
      eventType = EventType.MULTIPLE_PERSONS;
    }

    return this.prisma.event.create({
      data: {
        cameraId: createEventDto.cameraId,
        eventType,
        personCount: createEventDto.personCount,
        confidence: createEventDto.confidence,
        snapshotPath: createEventDto.snapshotPath,
        description: createEventDto.description,
      },
      include: {
        camera: {
          select: {
            id: true,
            name: true,
            location: true,
          }
        }
      }
    });
  }

  async findAll(limit = 50, offset = 0): Promise<Event[]> {
    return this.prisma.event.findMany({
      take: limit,
      skip: offset,
      orderBy: {
        createdAt: 'desc'
      },
      include: {
        camera: {
          select: {
            id: true,
            name: true,
            location: true,
          }
        }
      }
    });
  }

  async findById(id: number): Promise<Event> {
    const event = await this.prisma.event.findUnique({
      where: { id },
      include: {
        camera: {
          select: {
            id: true,
            name: true,
            location: true,
          }
        }
      }
    });

    if (!event) {
      throw new NotFoundException(`Event with ID ${id} not found`);
    }

    return event;
  }

  async findByCamera(cameraId: number, limit = 50): Promise<Event[]> {
    return this.prisma.event.findMany({
      where: { cameraId },
      take: limit,
      orderBy: {
        createdAt: 'desc'
      },
      include: {
        camera: {
          select: {
            id: true,
            name: true,
            location: true,
          }
        }
      }
    });
  }

  async findUnresolved(): Promise<Event[]> {
    return this.prisma.event.findMany({
      where: { isResolved: false },
      orderBy: {
        createdAt: 'desc'
      },
      include: {
        camera: {
          select: {
            id: true,
            name: true,
            location: true,
          }
        }
      }
    });
  }

  async resolve(id: number): Promise<Event> {
    const event = await this.findById(id);

    return this.prisma.event.update({
      where: { id },
      data: {
        isResolved: true,
        resolvedAt: new Date(),
      },
      include: {
        camera: {
          select: {
            id: true,
            name: true,
            location: true,
          }
        }
      }
    });
  }

  async getEventStats() {
    const [total, unresolved, todayEvents] = await Promise.all([
      this.prisma.event.count(),
      this.prisma.event.count({ where: { isResolved: false } }),
      this.prisma.event.count({
        where: {
          createdAt: {
            gte: new Date(new Date().setHours(0, 0, 0, 0))
          }
        }
      })
    ]);

    return {
      total,
      unresolved,
      todayEvents,
      resolved: total - unresolved,
    };
  }
}