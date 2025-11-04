import {
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateCameraDto, UpdateCameraDto } from './dto/camera.dto';

@Injectable()
export class CameraService {
  constructor(private prisma: PrismaService) {}

  async create(createCameraDto: CreateCameraDto) {
    return this.prisma.camera.create({
      data: {
        name: createCameraDto.name,
        location: createCameraDto.location,
        streamUrl: createCameraDto.streamUrl,
        webrtcUrl: createCameraDto.webrtcUrl,
        description: createCameraDto.description,
        isActive: true,
      },
    });
  }

  async findAll() {
    return this.prisma.camera.findMany({
      include: {
        events: {
          take: 5,
          orderBy: {
            createdAt: 'desc'
          }
        }
      }
    });
  }

  async findById(id: number) {
    const camera = await this.prisma.camera.findUnique({
      where: { id },
      include: {
        events: {
          take: 10,
          orderBy: {
            createdAt: 'desc'
          }
        }
      }
    });

    if (!camera) {
      throw new NotFoundException(`Camera with ID ${id} not found`);
    }

    return camera;
  }

  async update(id: number, updateCameraDto: UpdateCameraDto) {
    await this.findById(id);

    return this.prisma.camera.update({
      where: { id },
      data: {
        ...(updateCameraDto.name && { name: updateCameraDto.name }),
        ...(updateCameraDto.location && { location: updateCameraDto.location }),
        ...(updateCameraDto.streamUrl && { streamUrl: updateCameraDto.streamUrl }),
        ...(updateCameraDto.webrtcUrl && { webrtcUrl: updateCameraDto.webrtcUrl }),
        ...(updateCameraDto.description && { description: updateCameraDto.description }),
        ...(updateCameraDto.isActive !== undefined && { isActive: updateCameraDto.isActive }),
      },
    });
  }

  async delete(id: number) {
    await this.findById(id);

    return this.prisma.camera.delete({
      where: { id },
    });
  }

  async getStats() {
    const [total, active, inactive] = await Promise.all([
      this.prisma.camera.count(),
      this.prisma.camera.count({ where: { isActive: true } }),
      this.prisma.camera.count({ where: { isActive: false } }),
    ]);

    return {
      total,
      active,
      inactive,
    };
  }
}