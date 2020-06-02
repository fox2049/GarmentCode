#!/bin/bash
# This script is needed to autorestart execution of simulating datapoints for a dataset in case of Maya\Qualoth hangs or crashes
# Use something like git bash to run this script on Win
# Note you might want to suppress Maya crash report requests to stop getting annoyin windows
#   * https://knowledge.autodesk.com/support/maya/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-Disable-or-Enable-Crash-Error-Reports-s.html
#   * https://forums.autodesk.com/t5/installation-licensing/disable-error-reporting/td-p/4071164 

# ensure killing is possible
# https://www.linuxjournal.com/article/10815

# Use Ctrl-C to stop this script after currently running mini-batch finishes
sigint()
{
   echo "Ctrl-C signal INT received, script ending after returning from datasim execution"
   exit 1
}
trap 'sigint'  INT

# -- Main calls --
num_samples=15
per_sample_delay=$((3*60))  # give about 3 min per sample before detecting Maya to hang
dataset=data_500_skirt_maya_coords_200601-17-09-33
config=custom_fabric_props_basic_body.json
ret_code=1
STARTTIME=$(date +%s)
while [ $ret_code != 0 ]  # failed for any reason
do
    # https://unix.stackexchange.com/questions/405337/bash-if-command-doesnt-finish-in-x-time
    # set timeout to catch hangs.
    # forse kill if not soft terminating
    timeout -k 30 $((num_samples * per_sample_delay)) d:/Autodesk/Maya2020/bin/mayapy.exe "./datasim.py" --data $dataset --minibatch $num_samples  --config $config
    ret_code=$?
    echo $ret_code   # if it's 124, the execution was finished by timeout

    # clear tmp files created by Qualoth -- they can be left after crashes && fill out all the free disk space
    find /tmp -regextype sed -regex "/tmp/tmp[0-9]*\.[0-9]*" -delete
done
ENDTIME=$(date +%s)
T=$(($ENDTIME - $STARTTIME))
echo "It took ${T} seconds to complete this task..."
printf "Pretty format: %02d d %02d:%02d %02d s\n" "$(($T/86400))" "$(($T/3600%24))" "$(($T/60%60))" "$(($T%60))"