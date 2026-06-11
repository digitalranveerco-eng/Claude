import {
  Body,
  Controller,
  Post,
  Req,
  Res,
  UseGuards,
} from '@nestjs/common';
import type { Request, Response } from 'express';
import { RolesGuard } from '../auth/roles.guard';

/**
 * Proxies an authenticated chat turn to the FastAPI AI orchestration layer and
 * streams the SSE response straight back to the client. The Core API is the
 * trust boundary: it resolves the caller's org + user from the session and
 * injects them, so the browser can never spoof tenancy.
 */
@Controller('chat')
@UseGuards(RolesGuard)
export class ChatController {
  private readonly aiBaseUrl =
    process.env.AI_SERVICE_URL ?? 'http://localhost:8000';

  @Post('stream')
  async stream(
    @Req() req: Request & { user: { id: string; orgId: string } },
    @Body() body: { sessionId: string; sectionId: string; message: string; history?: unknown[] },
    @Res() res: Response,
  ): Promise<void> {
    const upstream = await fetch(`${this.aiBaseUrl}/v1/chat/stream`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        org_id: req.user.orgId,
        user_id: req.user.id,
        session_id: body.sessionId,
        section_id: body.sectionId,
        user_message: body.message,
        history: body.history ?? [],
      }),
    });

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const reader = upstream.body?.getReader();
    if (!reader) {
      res.end();
      return;
    }
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(decoder.decode(value, { stream: true }));
    }
    res.end();
  }
}
