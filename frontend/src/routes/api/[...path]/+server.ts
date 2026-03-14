const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
import { fetchCSRFToken } from '$lib/index.server';
import { json } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
	const { url, params, request, fetch, cookies } = event;
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam);
}

/** @type {import('./$types').RequestHandler} */
export async function POST({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}` : '';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

export async function PATCH({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

export async function PUT({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

export async function DELETE({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

async function handleRequest(
	url: any,
	params: any,
	request: any,
	fetch: any,
	cookies: any,
	searchParam: string,
	requreTrailingSlash: boolean | undefined = false
) {
	const path = params.path;
	let targetUrl = `${endpoint}/api/${path}`;

	// Preserve global proxy contract for mutating requests.
	if (requreTrailingSlash && !targetUrl.endsWith('/')) {
		targetUrl += '/';
	}

	// Append query parameters to the path correctly
	targetUrl += searchParam; // This will add ?format=json or &format=json to the URL

	const headers = new Headers(request.headers);

	const isMutatingRequest = !['GET', 'HEAD', 'OPTIONS'].includes(request.method.toUpperCase());
	const sessionId = cookies.get('sessionid');
	let csrfToken: string | null = null;

	if (isMutatingRequest) {
		csrfToken = await fetchCSRFToken({ fetch, sessionId });
		if (!csrfToken) {
			return json({ error: 'CSRF token is missing or invalid' }, { status: 400 });
		}
	}

	const cookieParts: string[] = [];
	if (csrfToken) cookieParts.push(`csrftoken=${csrfToken}`);
	if (sessionId) cookieParts.push(`sessionid=${sessionId}`);
	const cookieHeader = cookieParts.join('; ');

	const forwardedHeaders = {
		...Object.fromEntries(headers)
	} as Record<string, string>;

	if (csrfToken) {
		forwardedHeaders['X-CSRFToken'] = csrfToken;
	}

	if (cookieHeader) {
		forwardedHeaders['Cookie'] = cookieHeader;
	}

	try {
		const response = await fetch(targetUrl, {
			method: request.method,
			headers: forwardedHeaders,
			body:
				request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined,
			credentials: 'include' // This line ensures cookies are sent with the request
		});

		if (response.status === 204) {
			return new Response(null, {
				status: 204,
				headers: response.headers
			});
		}

		const contentType = response.headers.get('content-type') || '';
		const cleanHeaders = new Headers(response.headers);
		cleanHeaders.delete('set-cookie');

		// Stream SSE responses through without buffering
		if (contentType.includes('text/event-stream')) {
			return new Response(response.body, {
				status: response.status,
				headers: cleanHeaders
			});
		}

		const responseData = await response.arrayBuffer();

		return new Response(responseData, {
			status: response.status,
			headers: cleanHeaders
		});
	} catch (error) {
		console.error('Error forwarding request:', error);
		return json({ error: 'Internal Server Error' }, { status: 500 });
	}
}
