import asyncio
import json
import logging
import time
import uuid
import websockets
import msgpack

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("simulated_world")


class SimulatedUnrealWorldClient:
    """Simulates the Unreal Engine world client that connects to LuckyRobots core"""

    def __init__(self, server_url="ws://localhost:3000/world"):
        """Initialize the simulated Unreal world client.

        Args:
            server_url: WebSocket URL to connect to
        """
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        self.should_run = True

        # Simulated robot state
        self.robot_state = {
            "left_wheel": 0,
            "right_wheel": 0,
            "arm_joint1": 0,
            "arm_joint2": 0,
        }

        # Counter for observations
        self.observation_counter = 0

    async def connect(self):
        """Connect to the LuckyRobots WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info(f"Connected to LuckyRobots server at {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from the LuckyRobots WebSocket server"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from server")

    async def send_message(self, message):
        """Send a message to the server

        Args:
            message: The message to send (will be converted to JSON)
        """
        if not self.connected or not self.websocket:
            logger.error("Cannot send message - not connected to server")
            return False

        try:
            await self.websocket.send(msgpack.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False
            return False

    def create_camera_data(self):
        """Create simulated camera data

        Returns:
            Dict containing simulated camera data
        """
        return {
            "cameraName": "front_camera",
            "dtype": "uint8",
            "shape": {"image_width": 640, "image_height": 480, "channel": 3},
            "filePath": f"/tmp/simulated_image_{self.observation_counter}.jpg",
        }

    def create_observation(self):
        """Create a simulated observation

        Returns:
            Dict containing the observation data
        """
        self.observation_counter += 1

        return {
            "timeStamp": int(time.time() * 1000),
            "id": f"observation_{self.observation_counter}",
            "observationState": self.robot_state.copy(),
            "observationCameras": [self.create_camera_data()],
        }

    async def handle_reset(self, message):
        """Handle a reset request from the server

        Args:
            message: The reset request message
        """
        # Extract request details
        request_id = message.get("request_id", f"unknown_{uuid.uuid4().hex}")
        seed = message.get("seed")

        # Reset the robot state
        self.robot_state = {
            "left_wheel": 0,
            "right_wheel": 0,
            "arm_joint1": 0,
            "arm_joint2": 0,
        }

        # Create observation
        observation = self.create_observation()

        # Create response
        response = {
            "type": "reset_response",
            "request_id": request_id,
            "success": True,
            "message": f"Reset successful with seed {seed if seed else 'None'}",
            "observation": observation,
            "info": {
                "status": "reset_complete",
                "seed": seed,
                "timestamp": time.time(),
            },
        }

        # Send response
        await self.send_message(response)
        logger.info(f"Sent reset response for request {request_id}")

    async def handle_step(self, message):
        """Handle a step request from the server

        Args:
            message: The step request message
        """

        # Extract request details
        request_id = message.get("request_id", f"{uuid.uuid4().hex}")
        pose = message.get("pose")
        twist = message.get("twist")

        # Create observation
        observation = self.create_observation()

        # Create response
        response = {
            "type": "step_response",
            "request_id": request_id,
            "success": True,
            "message": "Step successful",
            "observation": observation,
            "info": {"status": "step_complete", "timestamp": time.time()},
        }

        # Send response
        await self.send_message(response)

    async def run(self):
        """Run the client, connecting to the server and handling messages"""
        while self.should_run:
            if not self.connected:
                connected = await self.connect()
                if not connected:
                    # Wait before retry
                    await asyncio.sleep(5)
                    continue

            try:
                # Process incoming messages
                async for message in self.websocket:
                    try:
                        data = msgpack.unpackb(message)

                        # Handle different message types
                        if "type" in data:
                            if data["type"] == "reset":
                                await self.handle_reset(data)
                            elif data["type"] == "step":
                                await self.handle_step(data)
                            else:
                                logger.warning(f"Unknown message type: {data['type']}")
                        else:
                            logger.warning("Received message without type field")

                    except json.JSONDecodeError:
                        logger.error(f"Received invalid JSON: {message}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed by server")
                self.connected = False

                # Wait before reconnect
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                self.connected = False

                # Wait before reconnect
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the client"""
        self.should_run = False
        await self.disconnect()


async def main():
    """Main function to run the simulated Unreal world client"""
    client = SimulatedUnrealWorldClient()

    # Handle keyboard interrupt
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        await client.stop()
        logger.info("Simulated Unreal world client terminated")


if __name__ == "__main__":
    asyncio.run(main())
