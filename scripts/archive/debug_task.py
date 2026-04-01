from eden import Eden
import asyncio

async def test():
    app = Eden()
    print("App created")
    
    @app.task(retries=2)
    async def my_task():
        print("Executing my_task")
        return 42
    
    print("Task registered")
    
    await app.broker.startup()
    print("Broker started")
    
    await my_task.kiq()
    print("Task kiqed")
    
    await asyncio.sleep(0.5)
    print("Done")

if __name__ == "__main__":
    asyncio.run(test())
