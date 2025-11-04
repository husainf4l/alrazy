import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { UserModule } from './user/user.module';
import { CameraModule } from './camera/camera.module';
import { EventModule } from './event/event.module';
import { LockModule } from './lock/lock.module';
import configuration from './config/configuration';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [configuration],
    }),
    PrismaModule,
    AuthModule,
    UserModule,
    CameraModule,
    EventModule,
    LockModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
