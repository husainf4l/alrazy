import { IsEmail, IsString, MinLength, IsOptional } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class LoginDto {
  @ApiProperty({ example: 'husain' })
  @IsString()
  @MinLength(3)
  username: string;

  @ApiProperty({ example: 'password123' })
  @IsString()
  @MinLength(6)
  password: string;
}

export class RegisterDto {
  @ApiProperty({ example: 'husain@alrazy.com' })
  @IsEmail()
  email: string;

  @ApiProperty({ example: 'husain' })
  @IsString()
  @MinLength(3)
  username: string;

  @ApiProperty({ example: 'password123' })
  @IsString()
  @MinLength(6)
  password: string;

  @ApiProperty({ example: 'Husain', required: false })
  @IsOptional()
  @IsString()
  firstName?: string;

  @ApiProperty({ example: 'Al Razy', required: false })
  @IsOptional()
  @IsString()
  lastName?: string;
}
