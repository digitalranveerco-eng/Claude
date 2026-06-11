import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';

/**
 * Minimal RBAC guard placeholder. In production, validate the session (Auth.js /
 * Clerk) and attach `req.user = { id, orgId, role }`. Tenant isolation is then
 * enforced again at the DB layer via Postgres RLS (`SET LOCAL app.current_org`).
 */
@Injectable()
export class RolesGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest();
    if (!req.user?.id || !req.user?.orgId) {
      throw new UnauthorizedException('missing authenticated session');
    }
    return true;
  }
}
