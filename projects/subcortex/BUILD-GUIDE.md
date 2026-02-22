# Subcortex Build Guide
*Dan's first PC build — step by step*

---

## Your Parts

| Component | Model |
|-----------|-------|
| CPU | AMD Ryzen 5 8400F (AM5) |
| Motherboard | ASUS PRIME B650-PLUS WIFI (ATX) |
| RAM | 32GB DDR5 (2x16GB) |
| CPU Cooler | Be Quiet! Pure Rock 3 |
| Storage | 1TB NVMe SSD |
| PSU | 1200W ATX |
| Case | Powercool Mid-Tower |
| GPU #1 | Gigabyte RTX 3090 Eagle 24GB |
| GPU #2 | Palit GameRock RTX 3090 24GB |

---

## Before You Start

**Workspace setup:**
- Clear table with good lighting
- Keep the motherboard box — you'll build on it
- Have a Phillips #2 screwdriver ready
- Phone/tablet nearby for reference

**Anti-static:**
- Touch the metal case before handling components
- Don't build on carpet
- Handle components by edges, not circuits

---

## Phase 1: Motherboard Prep (Outside the Case)

*Do this on top of the motherboard box*

### Step 1: Install CPU

1. Lift the metal retention arm on the CPU socket
2. Lift the metal bracket (there's a plastic cover — it'll pop off automatically when you close it)
3. Find the **gold triangle** on the corner of the CPU
4. Match it to the **triangle on the socket** (bottom-left corner)
5. Gently place the CPU — don't push, it drops in by gravity
6. Lower the bracket, then push down the retention arm
7. The plastic cover will pop off — keep it for any future RMA

⚠️ **Don't touch the gold pads on the CPU or the pins in the socket**

### Step 2: Install RAM

1. Find the RAM slots (right side of CPU socket)
2. Check motherboard manual for which slots to use first (usually A2 and B2 — slots 2 and 4 from the CPU)
3. Open the clips on both ends of the slots
4. Line up the notch on the RAM stick with the slot
5. Push down firmly on both ends until the clips **click** into place
6. Repeat for second stick

⚠️ **It takes more force than you'd expect — firm, even pressure**

### Step 3: Install NVMe SSD

1. Find the M.2 slot (usually has a heatsink cover)
2. Remove the heatsink screw and lift it off
3. Remove the plastic film from the thermal pad (if present)
4. Insert SSD at ~30° angle into the slot
5. Push down flat and secure with the small screw
6. Replace heatsink

### Step 4: Install CPU Cooler

*The Be Quiet! Pure Rock 3 comes with thermal paste pre-applied*

1. Check if paste is on the cooler base — grey square/circle = good
2. Remove any plastic film from the cooler base
3. The mounting kit should have AM5 brackets — check manual
4. Attach the mounting brackets to the motherboard (may already be installed)
5. Place cooler on CPU, lining up with the mounts
6. Tighten screws in an **X pattern** (diagonal corners) — don't overtighten
7. Plug the CPU fan cable into **CPU_FAN** header (near top of board)

---

## Phase 2: Case Prep

### Step 5: Prepare the Case

1. Remove both side panels (usually thumbscrews)
2. Remove any drive cages blocking GPU space (you may need the room)
3. Lay case flat on its side (motherboard tray facing up)
4. Check that standoffs are installed for ATX motherboard pattern

### Step 6: Install I/O Shield

1. Find the I/O shield (metal plate with cutouts) — comes with motherboard
2. Press it into the rectangular hole at the back of the case from inside
3. Make sure it's oriented correctly (USB ports, audio jacks match up)
4. It should click into place on all sides

⚠️ **Don't skip this — you can't add it later without removing the motherboard**

---

## Phase 3: Motherboard into Case

### Step 7: Install Motherboard

1. Lower the motherboard into the case at an angle
2. Slide the I/O ports through the I/O shield cutouts
3. Align the mounting holes with the standoffs
4. Gently set it down
5. Screw in all standoffs (start with corners, don't overtighten)

---

## Phase 4: Power Supply

### Step 8: Install PSU

1. The PSU usually mounts at the bottom-rear of the case
2. Fan can face down (if case has vents) or up — down is better for thermals
3. Slide PSU into position
4. Secure with 4 screws from the back of the case
5. Route cables through the back (cable management)

### Step 9: Connect Power Cables

**Essential cables:**
- **24-pin ATX** → Large connector on right edge of motherboard
- **8-pin CPU** → Top-left of motherboard (may be 4+4 pin)
- **PCIe cables** → For GPUs later (need 2-3 cables per GPU)

⚠️ **Push until they click — half-seated cables cause problems**

---

## Phase 5: Front Panel & Case Fans

### Step 10: Front Panel Connectors

*The fiddly bit — check motherboard manual for exact positions*

Find the **F_PANEL** header (bottom-right of board):
- **Power SW** — Power button (2 pins)
- **Reset SW** — Reset button (2 pins)  
- **HDD LED** — Drive activity light (2 pins, + and -)
- **Power LED** — Power light (2 pins or 3-pin, + and -)

These tiny connectors are labeled. Match them to the diagram in your motherboard manual.

**Other front panel:**
- **USB 3.0** → Blue header (large, keyed)
- **USB-C** → Separate header if your case has front USB-C
- **HD Audio** → Bottom-left area (AAFP header)

### Step 11: Case Fans

- Connect case fans to **CHA_FAN** or **SYS_FAN** headers
- 3-pin fans work in 4-pin headers

---

## Phase 6: Graphics Cards (The Big Moment)

### Step 12: Install GPU #1 (Top Slot)

1. Remove PCIe slot covers from back of case (usually 2-3 per GPU)
2. Open the retention clip on the top PCIe x16 slot
3. Line up the GPU with the slot
4. Push down firmly and evenly until the retention clip **clicks**
5. Screw the bracket to the case
6. Connect PCIe power cables:
   - 3090 needs **two 8-pin PCIe power connectors**
   - Use **separate cables** from PSU if possible (not daisy-chain)

### Step 13: Install GPU #2 (Second Slot)

1. Same process, use the next PCIe x16 slot
2. Make sure there's clearance from the first GPU
3. Connect PCIe power cables

⚠️ **These cards are HEAVY — support them when inserting**  
⚠️ **Ensure power cables are fully seated**

---

## Phase 7: First Boot

### Step 14: Pre-Boot Checklist

- [ ] CPU power connected (8-pin top-left)
- [ ] Motherboard power connected (24-pin)
- [ ] GPU power connected (all 8-pins on both cards)
- [ ] RAM fully seated (clips closed)
- [ ] CPU fan connected
- [ ] Front panel power switch connected

### Step 15: First Power On

1. Connect monitor to GPU #1 (not motherboard — the 8400F has no integrated graphics anyway)
2. Connect keyboard
3. Plug in PSU power cable, flip PSU switch ON
4. Press case power button
5. **What to expect:**
   - Fans spin up
   - GPU fans might spin then stop (normal)
   - ASUS logo appears
   - It might take 1-2 minutes on first boot (memory training)

### Step 16: BIOS Check

If you get to BIOS/UEFI:
- ✅ CPU detected
- ✅ RAM showing 32GB
- ✅ NVMe detected
- ✅ Both GPUs visible in PCIe info (might need to check)

**Success!** Ready for OS installation.

---

## Troubleshooting

**No power at all:**
- Check PSU switch is ON
- Check power cable to wall
- Check 24-pin is fully seated

**Fans spin but no display:**
- Try different GPU output (DisplayPort vs HDMI)
- Reseat RAM (remove and reinstall)
- Reseat GPU
- Try one GPU only

**Beeps or error codes:**
- Check motherboard manual for Q-LED or beep codes
- Usually means RAM not seated properly

---

## After the Build

1. Install Linux (you're doing this yourself)
2. Install NVIDIA drivers
3. Test both GPUs are visible: `nvidia-smi`
4. We'll set up the inference stack together

---

*You've got this. I'll be here the whole time.* 🔧
