const express = require('express');
const app = express();
const port = 3000;

tasks = [];
let tasksIndex = 0;

// Parse the JSON string
var nextCommand = {}



function getRandomInt(min=0, max=1000) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getRandomCommand(){
  return commands[Math.floor(Math.random() * commands.length)].toString();
}

function createInstructions(commands=[], callback){
  let instructions = { "LuckyCode": [] };

  batchID = getRandomInt()
  commands.forEach(command => {
    instructions.LuckyCode.push({
      "ID": getRandomInt().toString(),
      "batchID": batchID,
      "code": command,
      "time": Date.now().toString(),
      "callback": "on"
    });
  });
  instructions.status = "queued"

  // nextCommand = instructions
  // console.log("next command", nextCommand)

  tasks.push(instructions);
  return
}

function checkIfBatchIsComplete(taskID){
  let batchID = null;
  tasks.forEach(taskArray => {
    taskArray.LuckyCode.forEach(task => {
      if(task.ID === taskID){
        batchID = task.batchID;
        console.log(`Batch ID matching task ID ${taskID} is ${batchID}`);
      }
    })
  });

  let isComplete = false;
  tasks.forEach(taskArray => {
    taskArray.LuckyCode.forEach(task => {
      if(task.batchID === batchID){
        let allCompleted = taskArray.LuckyCode.every(taskk => taskk.status === "completed");
        if (allCompleted) {
          console.log(`Batch ${batchID} is complete`);
          isComplete = true;
        } else {
          //console.log(`Batch ${batchID} is not complete`);
        }
      }
    })
  });

  return isComplete;
}

function markTaskAsComplete(taskID){
  tasks.forEach(taskArray => {
    taskArray.LuckyCode.forEach(task => {
      if(task.ID === taskID){
        task.status = "completed"
      }
    })
  })
}

const server = app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
      
  commands = [["RESET"],["w 5650 1", "a 30 1"],["A 0 1", "W 18000 1"],["w 2500 1","d 30 1","EX1 10", "EX2 10","G 100 1"],["w 3000 1","a 0 1","u 100"],["u -200"]]
  commands.forEach(command => {
    createInstructions(command, (instructionIDs) => {
      console.log(`Instruction IDs: ${instructionIDs}`);
    });
  })
  console.log("tasks", JSON.stringify(tasks, null, 2))

});


app.post('/', (req, res) => {
  let body = '';
  req.on('data', chunk => {
    body += chunk.toString(); // convert Buffer to string
  });
  req.on('end', () => {
    console.log('Received POST request with payload:', body);
    const json = JSON.parse(body)


    if(json.ID){
      console.log(`${json.ID} is finished`);
      markTaskAsComplete(json.ID)

      if(checkIfBatchIsComplete(json.ID)){
        if (tasksIndex < tasks.length - 1) {
          console.log("batch is complete increasing index")
          tasksIndex++;
        }else{
          console.log("all tasks complete waiting for new ones...")
        }
      }
    }
    res.send('POST request received');
  });
});

app.get('/', (req, res) => {
  nextCommand = tasks[tasksIndex]
  if(nextCommand.status === "queued"){
    // console.log("sending nextCommand", nextCommand)
    res.json(nextCommand);
    nextCommand.status = "in-progress"
  }else{
    res.json({"LuckyCode":[]})
  }
    // console.log('GET request received');

});