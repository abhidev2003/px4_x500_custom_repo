# Instructions for Teammates

Hey team, 

We've finalized the custom PX4 SITL simulation environment for our `x500_custom` drone! 

Because PX4 is extremely strict about where simulated models can be loaded from, I've created a custom git repository and an installer script that securely copies the files into your local PX4 build environments.

## How to get the custom drone on your PC

You must already have [PX4-Autopilot](https://github.com/PX4/PX4-Autopilot) cloned on your computer.

**1. Clone the custom repository**
Clone this anywhere on your PC (e.g., your home directory):
```bash
git clone https://github.com/abhidev2003/px4_x500_custom_repo.git
cd px4_x500_custom_repo
```

**2. Run the installer script**
If your PX4 folder is located at the default `~/PX4-Autopilot`, you can just run this without arguments:
```bash
./install.sh
```
*(If your PX4 is located somewhere else, run `./install.sh /path/to/your/PX4-Autopilot`)*

**3. Launch the simulation**
To fly the drone, simply navigate to your PX4 folder and build the target:
```bash
cd ~/PX4-Autopilot
make px4_sitl gz_x500_custom
```

> **⚠️ CRITICAL DIRECTIVE (For both humans and Antigravity AI)**
> 
> The `x500_custom` drone is highly volatile and will continue to go through active iterations and structural changes. 
> 
> **MANDATORY RULE:** Before beginning *any* new workflow or making modifications to this simulation setup (especially if you are using your Antigravity AI instance), you MUST text `abhidev` (the x500_custom author) to receive explicit confirmation and the latest status. 
> 
> Do not proceed with workflow execution until clearance from `abhidev` is achieved. The repo's README is updated to explicitly enforce this behavior for your AI assistants.
