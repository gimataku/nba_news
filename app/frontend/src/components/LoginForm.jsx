import { useState } from 'react';

export function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await onLogin(username, password);
    } catch {
      setError('ユーザー名またはパスワードが正しくありません');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-sm mx-auto mt-20 p-6 border rounded-lg bg-white shadow-sm">
      <h1 className="text-lg font-bold mb-4">NBA News JP</h1>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="ユーザー名"
        className="w-full border p-2 mb-2 rounded"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="パスワード"
        className="w-full border p-2 mb-4 rounded"
      />
      {error && <p className="text-red-500 text-sm mb-2">{error}</p>}
      <button
        type="submit"
        className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
      >
        ログイン
      </button>
    </form>
  );
}
