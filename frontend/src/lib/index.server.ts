const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

type FetchCSRFTokenOptions = {
	fetch?: typeof fetch;
	sessionId?: string;
};

export const fetchCSRFToken = async (options: FetchCSRFTokenOptions = {}) => {
	const fetchFn = options.fetch ?? fetch;
	const headers = new Headers();

	if (options.sessionId) {
		headers.set('Cookie', `sessionid=${options.sessionId}`);
	}

	const csrfTokenFetch = await fetchFn(`${serverEndpoint}/csrf/`, {
		headers
	});
	if (csrfTokenFetch.ok) {
		const csrfToken = await csrfTokenFetch.json();
		return csrfToken.csrfToken;
	} else {
		return null;
	}
};
