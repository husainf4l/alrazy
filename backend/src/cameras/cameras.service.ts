import {
  Injectable,
  NotFoundException,
  ForbiddenException,
  BadRequestException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { 
  CreateCameraDto, 
  UpdateCameraDto, 
  GrantCameraAccessDto,
  TestCameraConnectionDto 
} from './dto/camera.dto';
import { UserRole, CameraAccessLevel } from '@prisma/client';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

@Injectable()
export class CamerasService {
  constructor(private prisma: PrismaService) {}

  async create(createCameraDto: CreateCameraDto, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    // Check permissions
    if (user.role !== UserRole.SUPER_ADMIN && 
        user.role !== UserRole.COMPANY_ADMIN &&
        user.companyId !== createCameraDto.companyId) {
      throw new ForbiddenException('Access denied to create cameras for this company');
    }

    // Verify company exists
    const company = await this.prisma.company.findUnique({
      where: { id: createCameraDto.companyId },
    });

    if (!company) {
      throw new NotFoundException('Company not found');
    }

    // Check if camera URL already exists
    const existingCamera = await this.prisma.camera.findFirst({
      where: { rtspUrl: createCameraDto.rtspUrl },
    });

    if (existingCamera) {
      throw new BadRequestException('Camera with this RTSP URL already exists');
    }

    return this.prisma.camera.create({
      data: createCameraDto,
      include: {
        company: {
          select: { id: true, name: true },
        },
        adminUser: {
          select: { id: true, username: true, firstName: true, lastName: true },
        },
        userAccess: {
          include: {
            user: {
              select: { id: true, username: true, firstName: true, lastName: true },
            },
          },
        },
      },
    });
  }

  async findAll(userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    let whereClause = {};

    // Filter cameras based on user role and access - more restrictive approach
    if (user.role === UserRole.SUPER_ADMIN) {
      // Super admins can see all cameras in their company or all if no company restriction
      if (user.companyId) {
        whereClause = { companyId: user.companyId };
      } else {
        whereClause = {}; // All cameras for super admin without company
      }
    } else if (user.role === UserRole.COMPANY_ADMIN) {
      // Company admins can only see cameras in their company
      whereClause = { companyId: user.companyId };
    } else if (user.role === UserRole.MANAGER) {
      // Managers can see cameras in their company
      whereClause = { companyId: user.companyId };
    } else {
      // Regular users can only see cameras they have explicit access to
      whereClause = {
        OR: [
          { adminUserId: userId }, // Cameras they admin
          { userAccess: { some: { userId } } }, // Cameras they have access to
        ],
      };
    }

    return this.prisma.camera.findMany({
      where: whereClause,
      include: {
        company: {
          select: { id: true, name: true },
        },
        adminUser: {
          select: { id: true, username: true, firstName: true, lastName: true },
        },
        userAccess: {
          include: {
            user: {
              select: { id: true, username: true, firstName: true, lastName: true },
            },
          },
        },
        _count: {
          select: {
            recordings: true,
            alerts: true,
          },
        },
      },
    });
  }

  async findAllCameras() {
    // Return all cameras in the system - no user-based filtering
    return this.prisma.camera.findMany({
      include: {
        company: {
          select: { id: true, name: true },
        },
        adminUser: {
          select: { id: true, username: true, firstName: true, lastName: true },
        },
        userAccess: {
          include: {
            user: {
              select: { id: true, username: true, firstName: true, lastName: true },
            },
          },
        },
        _count: {
          select: {
            recordings: true,
            alerts: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  async findOne(id: number, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    const camera = await this.prisma.camera.findUnique({
      where: { id },
      include: {
        company: true,
        adminUser: {
          select: { id: true, username: true, firstName: true, lastName: true },
        },
        userAccess: {
          include: {
            user: {
              select: { id: true, username: true, firstName: true, lastName: true },
            },
          },
        },
        recordings: {
          take: 10,
          orderBy: { createdAt: 'desc' },
        },
        alerts: {
          take: 10,
          orderBy: { createdAt: 'desc' },
        },
      },
    });

    if (!camera) {
      throw new NotFoundException('Camera not found');
    }

    // Check access permissions
    const hasAccess = this.checkCameraAccess(camera, user);
    if (!hasAccess) {
      throw new ForbiddenException('Access denied to this camera');
    }

    return camera;
  }

  async update(id: number, updateCameraDto: UpdateCameraDto, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    const camera = await this.prisma.camera.findUnique({
      where: { id },
      include: { userAccess: true },
    });

    if (!camera) {
      throw new NotFoundException('Camera not found');
    }

    // Check permissions
    const canManage = this.checkCameraManageAccess(camera, user);
    if (!canManage) {
      throw new ForbiddenException('Access denied to manage this camera');
    }

    return this.prisma.camera.update({
      where: { id },
      data: updateCameraDto,
      include: {
        company: {
          select: { id: true, name: true },
        },
        adminUser: {
          select: { id: true, username: true, firstName: true, lastName: true },
        },
        userAccess: {
          include: {
            user: {
              select: { id: true, username: true, firstName: true, lastName: true },
            },
          },
        },
      },
    });
  }

  async remove(id: number, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    const camera = await this.prisma.camera.findUnique({
      where: { id },
    });

    if (!camera) {
      throw new NotFoundException('Camera not found');
    }

    // Only super admins and camera admins can delete cameras
    if (user.role !== UserRole.SUPER_ADMIN && 
        user.role !== UserRole.COMPANY_ADMIN &&
        camera.adminUserId !== userId) {
      throw new ForbiddenException('Access denied to delete this camera');
    }

    return this.prisma.camera.delete({
      where: { id },
    });
  }

  async grantAccess(cameraId: number, grantAccessDto: GrantCameraAccessDto, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    const camera = await this.prisma.camera.findUnique({
      where: { id: cameraId },
    });

    if (!camera) {
      throw new NotFoundException('Camera not found');
    }

    // Check permissions to grant access
    const canManage = this.checkCameraManageAccess(camera, user);
    if (!canManage) {
      throw new ForbiddenException('Access denied to manage camera access');
    }

    // Verify all users exist and belong to the same company
    const users = await this.prisma.user.findMany({
      where: {
        id: { in: grantAccessDto.userIds },
        companyId: camera.companyId,
      },
    });

    if (users.length !== grantAccessDto.userIds.length) {
      throw new BadRequestException('Some users not found or not in the same company');
    }

    // Grant access to all users
    const accessRecords = await Promise.all(
      grantAccessDto.userIds.map(async (targetUserId) => {
        return this.prisma.cameraUserAccess.upsert({
          where: {
            cameraId_userId: {
              cameraId,
              userId: targetUserId,
            },
          },
          update: {
            accessLevel: grantAccessDto.accessLevel,
            grantedBy: userId,
          },
          create: {
            cameraId,
            userId: targetUserId,
            accessLevel: grantAccessDto.accessLevel,
            grantedBy: userId,
          },
          include: {
            user: {
              select: { id: true, username: true, firstName: true, lastName: true },
            },
          },
        });
      }),
    );

    return accessRecords;
  }

  async revokeAccess(cameraId: number, targetUserId: number, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    const camera = await this.prisma.camera.findUnique({
      where: { id: cameraId },
    });

    if (!camera) {
      throw new NotFoundException('Camera not found');
    }

    // Check permissions
    const canManage = this.checkCameraManageAccess(camera, user);
    if (!canManage) {
      throw new ForbiddenException('Access denied to manage camera access');
    }

    return this.prisma.cameraUserAccess.deleteMany({
      where: {
        cameraId,
        userId: targetUserId,
      },
    });
  }


  private checkCameraAccess(camera: any, user: any): boolean {
    // Super admins have access to all cameras
    if (user.role === UserRole.SUPER_ADMIN) {
      return true;
    }

    // Company admins have access to all cameras in their company
    if (user.role === UserRole.COMPANY_ADMIN && user.companyId === camera.companyId) {
      return true;
    }

    // Camera admin has access
    if (camera.adminUserId === user.id) {
      return true;
    }

    // Check if user has explicit access
    const hasUserAccess = camera.userAccess?.some(access => access.userId === user.id);
    return hasUserAccess || false;
  }

  private checkCameraManageAccess(camera: any, user: any): boolean {
    // Super admins can manage all cameras
    if (user.role === UserRole.SUPER_ADMIN) {
      return true;
    }

    // Company admins can manage cameras in their company
    if (user.role === UserRole.COMPANY_ADMIN && user.companyId === camera.companyId) {
      return true;
    }

    // Camera admin can manage the camera
    if (camera.adminUserId === user.id) {
      return true;
    }

    // Check if user has ADMIN or MANAGER access level
    const userAccess = camera.userAccess?.find(access => access.userId === user.id);
    return userAccess?.accessLevel === CameraAccessLevel.ADMIN || 
           userAccess?.accessLevel === CameraAccessLevel.MANAGER;
  }

  async updateCameraStatus(cameraId: number, isOnline: boolean, lastConnectedAt?: Date) {
    return this.prisma.camera.update({
      where: { id: cameraId },
      data: {
        isOnline,
        lastConnectedAt: lastConnectedAt || new Date(),
        lastHealthCheck: new Date(),
      },
    });
  }
}
