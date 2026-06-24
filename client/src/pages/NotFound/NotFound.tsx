import { Link } from 'react-router-dom';


const NotFound = () => (
  <main className="grid min-h-[70vh] place-items-center p-6 text-center">
    <div>
      <p className="text-6xl font-bold text-primary">404</p>
      <h1 className="mt-4 text-xl font-semibold">页面不存在</h1>
      <Link to="/" className="mt-4 inline-block text-sm text-primary underline">
        返回图片库
      </Link>
    </div>
  </main>
);

export default NotFound;
