import { Injectable, NotFoundException, ForbiddenException, ConflictException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateUserDto, UpdateUserDto, UserRole } from './dto/user.dto';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class UsersService {
  constructor(private prisma: PrismaService) {}

  async create(createUserDto: CreateUserDto, currentUserId: number) {
    const currentUser = await this.prisma.user.findUnique({
      where: { id: currentUserId },
    });

    if (!currentUser) {
      throw new NotFoundException('Current user not found');
    }

    // Check permissions
    if (currentUser.role !== UserRole.SUPER_ADMIN && 
        currentUser.role !== UserRole.COMPANY_ADMIN) {
      throw new ForbiddenException('Access denied');
    }

    // Company admins can only create users in their company
    if (currentUser.role === UserRole.COMPANY_ADMIN && 
        createUserDto.companyId !== currentUser.companyId) {
      throw new ForbiddenException('Can only create users in your company');
    }

    // Check if email or username already exists
    const existingUser = await this.prisma.user.findFirst({
      where: {
        OR: [
          { email: createUserDto.email },
          { username: createUserDto.username },
        ],
      },
    });

    if (existingUser) {
      throw new ConflictException('Email or username already exists');
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(createUserDto.password, 10);

    const user = await this.prisma.user.create({
      data: {
        ...createUserDto,
        password: hashedPassword,
        role: createUserDto.role || UserRole.USER,
      },
      select: {
        id: true,
        email: true,
        username: true,
        firstName: true,
        lastName: true,
        phone: true,
        role: true,
        companyId: true,
        isActive: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    return user;
  }

  async findAll(currentUserId: number) {
    const currentUser = await this.prisma.user.findUnique({
      where: { id: currentUserId },
    });

    if (!currentUser) {
      throw new NotFoundException('Current user not found');
    }

    let whereClause = {};

    // Super admin can see all users
    if (currentUser.role === UserRole.SUPER_ADMIN) {
      whereClause = {};
    } 
    // Company admin can see users in their company
    else if (currentUser.role === UserRole.COMPANY_ADMIN) {
      whereClause = { companyId: currentUser.companyId };
    } 
    // Regular users can only see themselves
    else {
      whereClause = { id: currentUserId };
    }

    const users = await this.prisma.user.findMany({
      where: whereClause,
      select: {
        id: true,
        email: true,
        username: true,
        firstName: true,
        lastName: true,
        phone: true,
        role: true,
        companyId: true,
        isActive: true,
        createdAt: true,
        updatedAt: true,
        company: {
          select: {
            id: true,
            name: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    return users;
  }

  async findOne(id: number, currentUserId: number) {
    const currentUser = await this.prisma.user.findUnique({
      where: { id: currentUserId },
    });

    if (!currentUser) {
      throw new NotFoundException('Current user not found');
    }

    const user = await this.prisma.user.findUnique({
      where: { id },
      select: {
        id: true,
        email: true,
        username: true,
        firstName: true,
        lastName: true,
        phone: true,
        role: true,
        companyId: true,
        isActive: true,
        createdAt: true,
        updatedAt: true,
        company: {
          select: {
            id: true,
            name: true,
          },
        },
      },
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    // Check permissions
    if (currentUser.role !== UserRole.SUPER_ADMIN && 
        currentUser.role !== UserRole.COMPANY_ADMIN && 
        currentUser.id !== id) {
      throw new ForbiddenException('Access denied');
    }

    if (currentUser.role === UserRole.COMPANY_ADMIN && 
        user.companyId !== currentUser.companyId) {
      throw new ForbiddenException('Access denied');
    }

    return user;
  }

  async update(id: number, updateUserDto: UpdateUserDto, currentUserId: number) {
    const currentUser = await this.prisma.user.findUnique({
      where: { id: currentUserId },
    });

    if (!currentUser) {
      throw new NotFoundException('Current user not found');
    }

    const user = await this.prisma.user.findUnique({
      where: { id },
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    // Check permissions
    if (currentUser.role !== UserRole.SUPER_ADMIN && 
        currentUser.role !== UserRole.COMPANY_ADMIN && 
        currentUser.id !== id) {
      throw new ForbiddenException('Access denied');
    }

    if (currentUser.role === UserRole.COMPANY_ADMIN && 
        user.companyId !== currentUser.companyId) {
      throw new ForbiddenException('Access denied');
    }

    // Check if email or username already exists (excluding current user)
    if (updateUserDto.email || updateUserDto.username) {
      const existingUser = await this.prisma.user.findFirst({
        where: {
          AND: [
            { id: { not: id } },
            {
              OR: [
                updateUserDto.email ? { email: updateUserDto.email } : {},
                updateUserDto.username ? { username: updateUserDto.username } : {},
              ].filter(condition => Object.keys(condition).length > 0),
            },
          ],
        },
      });

      if (existingUser) {
        throw new ConflictException('Email or username already exists');
      }
    }

    const updatedUser = await this.prisma.user.update({
      where: { id },
      data: updateUserDto,
      select: {
        id: true,
        email: true,
        username: true,
        firstName: true,
        lastName: true,
        phone: true,
        role: true,
        companyId: true,
        isActive: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    return updatedUser;
  }

  async remove(id: number, currentUserId: number) {
    const currentUser = await this.prisma.user.findUnique({
      where: { id: currentUserId },
    });

    if (!currentUser) {
      throw new NotFoundException('Current user not found');
    }

    const user = await this.prisma.user.findUnique({
      where: { id },
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    // Check permissions
    if (currentUser.role !== UserRole.SUPER_ADMIN && 
        currentUser.role !== UserRole.COMPANY_ADMIN) {
      throw new ForbiddenException('Access denied');
    }

    if (currentUser.role === UserRole.COMPANY_ADMIN && 
        user.companyId !== currentUser.companyId) {
      throw new ForbiddenException('Access denied');
    }

    // Cannot delete yourself
    if (currentUser.id === id) {
      throw new ForbiddenException('Cannot delete yourself');
    }

    await this.prisma.user.delete({
      where: { id },
    });

    return { message: 'User deleted successfully' };
  }
}