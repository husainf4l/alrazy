import { IsEmail, IsString, MinLength, IsOptional } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class LoginDto {
  @ApiProperty({ example: 'husain' })
  @IsString()
  @MinLength(3)
  username: string;

  @ApiProperty({ example: 'tt55oo77' })
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

  @ApiProperty({ example: 'tt55oo77' })
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

  @ApiProperty({ example: '+966501234567', required: false })
  @IsOptional()
  @IsString()
  phone?: string;

  @ApiProperty({ example: 1, required: false })
  @IsOptional()
  companyId?: number;
}

export class RefreshTokenDto {
  @ApiProperty()
  @IsString()
  refreshToken: string;
}
