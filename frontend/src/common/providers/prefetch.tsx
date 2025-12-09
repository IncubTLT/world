export const Prefetch = () => {
	return (
		// <>
		<link
			rel="preload"
			fetchPriority="high"
			as="image"
			href="/page/home/hi.JPG"
		/>
		// </>
	);
};
