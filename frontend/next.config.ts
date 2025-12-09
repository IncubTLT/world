import type { NextConfig } from "next";

const BASE_URL = "https://api-poketon.vingrig.com";

const nextConfig: NextConfig = {
	/* config options here */
	env: {
		BASE_URL: BASE_URL,
	},
};

export default nextConfig;
