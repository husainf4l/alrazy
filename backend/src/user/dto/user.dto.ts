import { IsNotEmpty, IsString, IsEmail, IsOptional, MinLength } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CreateUserDto {
  @ApiProperty({ description: 'Username' })
  @IsNotEmpty()
  @IsString()
  @MinLength(3)
  username: string;

  @ApiProperty({ description: 'Email address' })
  @IsNotEmpty()
  @IsEmail()
  email: string;

  @ApiProperty({ description: 'Password' })
  @IsNotEmpty()
  @IsString()
  @MinLength(6)
  password: string;

  @ApiProperty({ 
    description: 'First name',
    required: false 
  })
  @IsOptional()
  @IsString()
  firstName?: string;

  @ApiProperty({ 
    description: 'Last name',
    required: false 
  })
  @IsOptional()
  @IsString()
  lastName?: string;
}

export class UpdateUserDto {
  @ApiProperty({ 
    description: 'First name',
    required: false 
  })
  @IsOptional()
  @IsString()
  firstName?: string;

  @ApiProperty({ 
    description: 'Last name',
    required: false 
  })
  @IsOptional()
  @IsString()
  lastName?: string;

  @ApiProperty({ 
    description: 'Email address',
    required: false 
  })
  @IsOptional()
  @IsEmail()
  email?: string;
}

export class UserResponseDto {
  id: number;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  role: string;
  isActive: boolean;
  createdAt: Date;
}