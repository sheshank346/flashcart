"use client";

import { useEffect, useState } from "react";

const PRODUCT_ID = 1;

export default function Home() {
  const [stock, setStock] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/stock/${PRODUCT_ID}/`);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStock(data.remaining_stock);
    };

    return () => socket.close();
  }, []);

  const handleBuy = async () => {
    setLoading(true);
    setMessage("");

    const res = await fetch(`http://127.0.0.1:8000/api/buy/${PRODUCT_ID}/`, {
      method: "POST",
    });
    const data = await res.json();

    if (data.success) {
      setStock(data.remaining_stock);
      setMessage("Purchase successful!");
    } else {
      setMessage(data.message || "Something went wrong");
    }

    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-50 dark:bg-black">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg p-8 w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold mb-2 text-black dark:text-white">
          Flash Sale Item
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-6">₹499.00</p>

        <p className="text-lg font-semibold mb-6 text-black dark:text-white">
          {stock === null ? "Loading..." : `${stock} left in stock`}
        </p>

        <button
          onClick={handleBuy}
          disabled={loading || stock === 0}
          className="w-full py-3 rounded-full bg-black text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-800 transition-colors"
        >
          {loading ? "Processing..." : stock === 0 ? "Sold Out" : "Buy Now"}
        </button>

        {message && (
          <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
            {message}
          </p>
        )}
      </div>
    </div>
  );
}