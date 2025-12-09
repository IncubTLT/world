import axios, { type AxiosInstance } from "axios";

class CoreServer {
	core_backend: AxiosInstance;
	constructor() {
		this.core_backend = axios.create({
			baseURL: process.env.BASE_URL,
		});
	}

}

export const CORE_SERVER_BACKEND = new CoreServer();
