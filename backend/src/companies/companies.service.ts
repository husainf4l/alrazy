import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateCompanyDto, UpdateCompanyDto } from './dto/company.dto';
import { UserRole } from '@prisma/client';

@Injectable()
export class CompaniesService {
  constructor(private prisma: PrismaService) {}

  async create(createCompanyDto: CreateCompanyDto, userId: number) {
    // Only super admins can create companies
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    if (user.role !== UserRole.SUPER_ADMIN) {
      throw new ForbiddenException('Only super admins can create companies');
    }

    return this.prisma.company.create({
      data: createCompanyDto,
      include: {
        users: {
          select: {
            id: true,
            email: true,
            username: true,
            firstName: true,
            lastName: true,
            role: true,
            isActive: true,
          },
        },
        cameras: {
          select: {
            id: true,
            name: true,
            location: true,
            isActive: true,
            isOnline: true,
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

    // Super admins can see all companies, others only their own
    if (user.role === UserRole.SUPER_ADMIN) {
      return this.prisma.company.findMany({
        include: {
          users: {
            select: {
              id: true,
              email: true,
              username: true,
              firstName: true,
              lastName: true,
              role: true,
              isActive: true,
            },
          },
          cameras: {
            select: {
              id: true,
              name: true,
              location: true,
              isActive: true,
              isOnline: true,
            },
          },
        },
      });
    } else if (user.companyId) {
      return this.prisma.company.findMany({
        where: { id: user.companyId },
        include: {
          users: {
            select: {
              id: true,
              email: true,
              username: true,
              firstName: true,
              lastName: true,
              role: true,
              isActive: true,
            },
          },
          cameras: {
            select: {
              id: true,
              name: true,
              location: true,
              isActive: true,
              isOnline: true,
            },
          },
        },
      });
    } else {
      return [];
    }
  }

  async findOne(id: number, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    // Check access permissions
    if (user.role !== UserRole.SUPER_ADMIN && user.companyId !== id) {
      throw new ForbiddenException('Access denied to this company');
    }

    const company = await this.prisma.company.findUnique({
      where: { id },
      include: {
        users: {
          select: {
            id: true,
            email: true,
            username: true,
            firstName: true,
            lastName: true,
            role: true,
            isActive: true,
            createdAt: true,
            lastLoginAt: true,
          },
        },
        cameras: {
          include: {
            adminUser: {
              select: {
                id: true,
                username: true,
                firstName: true,
                lastName: true,
              },
            },
            userAccess: {
              include: {
                user: {
                  select: {
                    id: true,
                    username: true,
                    firstName: true,
                    lastName: true,
                  },
                },
              },
            },
          },
        },
      },
    });

    if (!company) {
      throw new NotFoundException('Company not found');
    }

    return company;
  }

  async update(id: number, updateCompanyDto: UpdateCompanyDto, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    // Check permissions
    if (user.role !== UserRole.SUPER_ADMIN && 
        user.role !== UserRole.COMPANY_ADMIN &&
        user.companyId !== id) {
      throw new ForbiddenException('Access denied to update this company');
    }

    const company = await this.prisma.company.findUnique({
      where: { id },
    });

    if (!company) {
      throw new NotFoundException('Company not found');
    }

    return this.prisma.company.update({
      where: { id },
      data: updateCompanyDto,
      include: {
        users: {
          select: {
            id: true,
            email: true,
            username: true,
            firstName: true,
            lastName: true,
            role: true,
            isActive: true,
          },
        },
        cameras: {
          select: {
            id: true,
            name: true,
            location: true,
            isActive: true,
            isOnline: true,
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

    // Only super admins can delete companies
    if (user.role !== UserRole.SUPER_ADMIN) {
      throw new ForbiddenException('Only super admins can delete companies');
    }

    const company = await this.prisma.company.findUnique({
      where: { id },
      include: { users: true, cameras: true },
    });

    if (!company) {
      throw new NotFoundException('Company not found');
    }

    // Check if company has active users or cameras
    if (company.users.length > 0) {
      throw new ForbiddenException('Cannot delete company with active users');
    }

    if (company.cameras.length > 0) {
      throw new ForbiddenException('Cannot delete company with active cameras');
    }

    return this.prisma.company.delete({
      where: { id },
    });
  }

  async getCompanyUsers(companyId: number, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    // Check access permissions
    if (user.role !== UserRole.SUPER_ADMIN && user.companyId !== companyId) {
      throw new ForbiddenException('Access denied to this company');
    }

    return this.prisma.user.findMany({
      where: { companyId },
      select: {
        id: true,
        email: true,
        username: true,
        firstName: true,
        lastName: true,
        phone: true,
        role: true,
        isActive: true,
        createdAt: true,
        lastLoginAt: true,
        cameraAccess: {
          include: {
            camera: {
              select: {
                id: true,
                name: true,
                location: true,
              },
            },
          },
        },
      },
    });
  }

  async getCompanyCameras(companyId: number, userId: number) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      throw new ForbiddenException('User not found');
    }

    // Check access permissions
    if (user.role !== UserRole.SUPER_ADMIN && user.companyId !== companyId) {
      throw new ForbiddenException('Access denied to this company');
    }

    // Verify company exists
    const company = await this.prisma.company.findUnique({
      where: { id: companyId },
    });

    if (!company) {
      throw new NotFoundException('Company not found');
    }

    // Get all cameras for the company
    return this.prisma.camera.findMany({
      where: { companyId },
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
}
