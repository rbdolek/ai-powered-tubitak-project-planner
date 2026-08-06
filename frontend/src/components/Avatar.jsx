export default function Avatar({ src, size = 32, alt = "avatar" }) {
    const url = src
        ? `${src}${src.includes("?") ? "&" : "?"}v=${Date.now()}`
        : "/default_avatar.png";
    return (
        <img
            src={url}
            width={size}
            height={size}
            className="rounded-full object-cover"
            alt={alt}
        />
    );
}
