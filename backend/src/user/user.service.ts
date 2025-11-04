import { Injectable, ConflictException, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateUserDto, UpdateUserDto } from './dto/user.dto';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class UserService {
  constructor(private prisma: PrismaService) {}

  async create(createUserDto: CreateUserDto) {
    // Check if user already exists
    const existingUser = await this.prisma.user.findFirst({
      where: {
        OR: [
          { email: createUserDto.email },
          { username: createUserDto.username },
        ]
      }
    });

    if (existingUser) {
      throw new ConflictException('User with this email or username already exists');
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(createUserDto.password, 10);

    return this.prisma.user.create({
      data: {
        username: createUserDto.username,
        email: createUserDto.email,
        password: hashedPassword,
        firstName: createUserDto.firstName,
        lastName: createUserDto.lastName,
        role: 'USER',
        isActive: true,
      },
      select: {
        id: true,
        username: true,
        email: true,
        firstName: true,
        lastName: true,
        role: true,
        isActive: true,
        createdAt: true,
      }
    });
  }

  async findAll() {
    return this.prisma.user.findMany({
      select: {
        id: true,
        username: true,
        email: true,
        firstName: true,
        lastName: true,
        role: true,
        isActive: true,
        createdAt: true,
      }
    });
  }

  async findById(id: number) {
    const user = await this.prisma.user.findUnique({
      where: { id },
      select: {
        id: true,
        username: true,
        email: true,
        firstName: true,
        lastName: true,
        role: true,
        isActive: true,
        createdAt: true,
      }
    });

    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }

    return user;
  }

  async findByUsername(username: string) {
    return this.prisma.user.findUnique({
      where: { username },
    });
  }

  async findByEmail(email: string) {
    return this.prisma.user.findUnique({
      where: { email },
    });
  }

  async update(id: number, updateUserDto: UpdateUserDto) {
    await this.findById(id);

    // Check if email is being updated and if it's already taken
    if (updateUserDto.email) {
      const existingUser = await this.prisma.user.findFirst({
        where: {
          email: updateUserDto.email,
          NOT: { id }
        }
      });

      if (existingUser) {
        throw new ConflictException('This email is already in use');
      }
    }

    return this.prisma.user.update({
      where: { id },
      data: {
        ...(updateUserDto.firstName && { firstName: updateUserDto.firstName }),
        ...(updateUserDto.lastName && { lastName: updateUserDto.lastName }),
        ...(updateUserDto.email && { email: updateUserDto.email }),
      },
      select: {
        id: true,
        username: true,
        email: true,
        firstName: true,
        lastName: true,
        role: true,
        isActive: true,
        createdAt: true,
      }
    });
  }

  async delete(id: number) {
    await this.findById(id);

    return this.prisma.user.delete({
      where: { id },
    });
  }

  async getUserStats() {
    const [total, admins, activeUsers] = await Promise.all([
      this.prisma.user.count(),
      this.prisma.user.count({ where: { role: 'ADMIN' } }),
      this.prisma.user.count({ where: { isActive: true } }),
    ]);

    return {
      total,
      admins,
      activeUsers,
      inactiveUsers: total - activeUsers,
    };
  }
}