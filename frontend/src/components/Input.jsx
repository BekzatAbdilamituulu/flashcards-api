export default function Input({ className = "", ...props }) {
  return (
    <input
      className={[
        "w-full min-h-11 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-black outline-none",
        "placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-600 focus:ring-offset-0",
        className,
      ].join(" ")}
      {...props}
    />
  );
}
