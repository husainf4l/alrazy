import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);

  // Global prefix
  app.setGlobalPrefix('api');

  // CORS
  app.enableCors({
    origin: configService.get<string[]>('cors.origin') || ['http://localhost:3000'],
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
    credentials: true,
  });

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  // Swagger documentation
  const config = new DocumentBuilder()
    .setTitle('Security System API')
    .setDescription('Person Detection & Door Lock Control System')
    .setVersion('1.0')
    .addBearerAuth()
    .addTag('Authentication', 'User authentication and registration')
    .addTag('Users', 'User management endpoints')
    .addTag('Cameras', 'Camera management endpoints')
    .addTag('Events', 'Event detection and monitoring')
    .addTag('Lock Control', 'Door lock/relay control endpoints')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document, {
    swaggerOptions: {
      persistAuthorization: true,
    },
  });

  const port = configService.get<number>('port');
  await app.listen(port || 3000);
  
  console.log(`✅ Security System Backend is running on: http://localhost:${port}`);
  console.log(`📚 API Documentation: http://localhost:${port}/docs`);
  console.log(`🔌 WebSocket ready at: ws://localhost:${port}`);
}
bootstrap();
