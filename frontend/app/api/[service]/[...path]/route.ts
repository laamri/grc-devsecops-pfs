type Context = {
  params: Promise<{ service: string; path: string[] }>;
};

async function proxy(request: Request, context: Context) {
  const { service, path } = await context.params;
  const resource = path.join('/');
  // Deliberately expose only the routes used by the current task UI.
  const isHealth = resource === 'health' && ['auth', 'task'].includes(service);
  const isTasks = service === 'task' && resource === 'tasks';
  if (!isHealth && !isTasks) {
    return Response.json({ error: 'Unknown API route' }, { status: 404 });
  }
  if (request.method === 'POST' && !isTasks) {
    return Response.json({ error: 'Method not allowed' }, { status: 405 });
  }

  // These variables are server-only and are evaluated at request time.
  const base = service === 'auth'
    ? process.env.AUTH_INTERNAL_URL || 'http://127.0.0.1:8001'
    : process.env.TASK_INTERNAL_URL || 'http://127.0.0.1:8002';
  const endpoint = isTasks ? '/tasks/' : '/health';
  try {
    const upstream = await fetch(`${base.replace(/\/$/, '')}${endpoint}`, {
      method: request.method,
      headers: { 'Content-Type': 'application/json' },
      body: request.method === 'POST' ? await request.text() : undefined,
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(5000),
    });
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') || 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return Response.json({ error: 'API unavailable' }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
