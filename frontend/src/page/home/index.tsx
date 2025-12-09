"use client";
import { CORE_CLIENT_BACKEND } from "@/common/network/core-client";
import Image from "next/image";
import { useEffect } from "react";

export const Home = () => {
	useEffect(() => {
		CORE_CLIENT_BACKEND.core_backend.get("/").then((res) => {
			console.log(res);
		});
	}, []);
	return (
		<div className="center flex-col">
			<p className="text-4xl font-bold">DCL</p>
			<Image
				src="/page/home/hi.JPG"
				className="rounded w-80 h-96"
				fetchPriority="high"
				priority
				alt="hi"
				width={600}
				height={700}
			/>
		</div>
	);
};
