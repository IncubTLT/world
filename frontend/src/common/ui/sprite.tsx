import Image from "next/image";
import { cn } from "../utils";

export type IconProps = {
	name: string;
	className: string;
	onClick?: () => void;
	style?: React.CSSProperties;
	isPng?: boolean;
	pathSprite?: TPath;
};

type TPath = "icons/filled";

export const Sprite: React.FC<IconProps> = ({
	name,
	className,
	onClick,
	style,
	isPng,
	pathSprite,
}) => {
	if (pathSprite) {
		return (
			<Image
				fetchPriority="high"
				priority
				src={`/${pathSprite}/${name}.${isPng ? "png" : "svg"}`}
				alt=""
				width={256}
				height={256}
				className={cn(
					typeof onClick === "function" && "cursor-pointer",
					className
				)}
				onClick={onClick}
				style={style}
			/>
		);
	}

	return (
		<svg
			role="graphics-symbol img"
			name={name}
			onClick={() => {}}
			onKeyDown={onClick}
			className={className}
			style={style}
		>
			<use xlinkHref={`/sprite.svg#${name}`} />
		</svg>
	);
};
