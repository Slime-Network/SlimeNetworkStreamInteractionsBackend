PORT=10902

while : # auto-resume: the code sometimes crash due to bug of gloo on some gpus
do
torchrun --nproc_per_node=1 \
        --master_port=$PORT \
    MeloTTS/melo/train.py --c 'VoiceTraining/config.json' --model 'voices' 

for PID in $(ps -aux | grep 'VoiceTraining/config.json' | grep python | awk '{print 1}')
do
    echo $PID
    kill -9 $PID
done
sleep 30
done