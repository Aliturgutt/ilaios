import Link from "next/link";
export default function NotFound() { return <div className="shell prose"><div className="eyebrow">404</div><h1>Page not found.</h1><p>The page you requested does not exist.</p><Link className="button" href="/">Return home</Link></div>; }
