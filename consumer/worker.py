"""
Worker Process Manager
Runs consumer workers to process article scraping tasks
"""
import asyncio
import sys
import os
from consumer.consumer import start_consumer

async def main():
    """
    Start a consumer worker.
    Worker ID can be passed as command line argument.
    """
    # Get worker ID from environment or command line
    worker_id = os.getenv('WORKER_ID')
    
    if not worker_id:
        worker_id = sys.argv[1] if len(sys.argv) > 1 else f"worker-{os.getpid()}"
    
    print(f"Starting worker: {worker_id}")
    print(f"   Redis: {os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}")
    print(f"   MongoDB: {os.getenv('MONGO_HOST', 'localhost')}:{os.getenv('MONGO_PORT', 27017)}")
    print("-" * 60)
    
    try:
        await start_consumer(worker_id)
    except KeyboardInterrupt:
        print(f"\nWorker {worker_id} stopped by user")
    except Exception as e:
        print(f"Worker {worker_id} crashed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())