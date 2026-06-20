import { useState, useEffect } from 'react';

export function GameSchedule({ token }) {
  const [games, setGames] = useState([]);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
    fetch(`/api/schedule?start_date=${today}&end_date=${nextWeek}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => setGames(d.games ?? []));
  }, [token]);

  if (games.length === 0) {
    return <p className="text-center text-gray-500 py-8">試合日程がありません</p>;
  }

  return (
    <div>
      {games.map((game) => (
        <GameRow key={game.game_id} game={game} />
      ))}
    </div>
  );
}

function GameRow({ game }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div className="border rounded p-3 mb-2 flex justify-between items-center bg-white shadow-sm">
      <span className="text-sm font-medium">
        {game.visitor_team} @ {game.home_team}
      </span>
      <span className="text-sm text-gray-500">{game.game_date}</span>

      {game.has_score && !revealed ? (
        <button
          onClick={() => setRevealed(true)}
          className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200"
        >
          スコアを表示
        </button>
      ) : revealed && game.home_score != null ? (
        <div className="flex flex-col items-end">
          <span className="font-mono text-sm">
            {game.visitor_score} - {game.home_score}
          </span>
          <button
            onClick={() => setRevealed(false)}
            className="text-xs text-gray-400 underline mt-1"
          >
            スコアを隠す
          </button>
        </div>
      ) : (
        <span className="text-gray-400 text-xs">{game.status}</span>
      )}
    </div>
  );
}
