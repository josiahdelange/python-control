"""test_margins.py
Demonstrate disk-based stability margin calculations.
"""

import os, sys, math
import numpy as np
import matplotlib.pyplot as plt
import control

if __name__ == '__main__':

    # Frequencies of interest
    omega = np.logspace(-1, 3, 1001)

    # Plant model
    P = control.ss([[0, 10],[-10, 0]], np.eye(2), [[1, 10], [-10, 1]], [[0, 0],[0, 0]])

    # Feedback controller
    K = control.ss([],[],[], [[1, -2], [0, 1]])

    # Output loop gain
    L = P*K
    print(f"Lo = {L}")

    print(f"------------- Balanced sensitivity function (S - T) -------------")
    DM, GM, PM = control.disk_margins(L, omega, 0.0) # balanced (S - T)
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {control.db2mag(min(GM))}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg\n\n")

    plt.figure(1)
    plt.subplot(3,3,1)
    plt.semilogx(omega, DM, label='$\\alpha$')
    plt.legend()
    plt.title('Disk Margin (Outputs)')
    plt.grid()
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    plt.figure(1)
    plt.subplot(3,3,4)
    plt.semilogx(omega, GM, label='$\\gamma_{m}$')
    plt.ylabel('Margin (dB)')
    plt.legend()
    plt.title('Disk-Based Gain Margin (Outputs)')
    plt.grid()
    plt.ylim([0, 40])
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    plt.figure(1)
    plt.subplot(3,3,7)
    plt.semilogx(omega, PM, label='$\\phi_{m}$')
    plt.ylabel('Margin (deg)')
    plt.legend()
    plt.title('Disk-Based Phase Margin (Outputs)')
    plt.grid()
    plt.ylim([0, 90])
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    #print(f"------------- Sensitivity function (S) -------------")
    #DM, GM, PM = control.disk_margins(L, omega, 1.0) # S-based (S)
    #print(f"min(DM) = {min(DM)}")
    #print(f"min(GM) = {control.db2mag(min(GM))}")
    #print(f"min(GM) = {min(GM)} dB")
    #print(f"min(PM) = {min(PM)} deg\n\n")

    #print(f"------------- Complementary sensitivity function (T) -------------")
    #DM, GM, PM = control.disk_margins(L, omega, -1.0) # T-based (T)
    #print(f"min(DM) = {min(DM)}")
    #print(f"min(GM) = {control.db2mag(min(GM))}")
    #print(f"min(GM) = {min(GM)} dB")
    #print(f"min(PM) = {min(PM)} deg\n\n")

    # Input loop gain
    L = K*P
    print(f"Li = {L}")

    print(f"------------- Balanced sensitivity function (S - T) -------------")
    DM, GM, PM = control.disk_margins(L, omega, 0.0) # balanced (S - T)
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {control.db2mag(min(GM))}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg\n\n")

    plt.figure(1)
    plt.subplot(3,3,2)
    plt.semilogx(omega, DM, label='$\\alpha$')
    plt.legend()
    plt.title('Disk Margin (Inputs)')
    plt.grid()
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    plt.figure(1)
    plt.subplot(3,3,5)
    plt.semilogx(omega, GM, label='$\\gamma_{m}$')
    plt.ylabel('Margin (dB)')
    plt.legend()
    plt.title('Disk-Based Gain Margin (Inputs)')
    plt.grid()
    plt.ylim([0, 40])
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    plt.figure(1)
    plt.subplot(3,3,8)
    plt.semilogx(omega, PM, label='$\\phi_{m}$')
    plt.ylabel('Margin (deg)')
    plt.legend()
    plt.title('Disk-Based Phase Margin (Inputs)')
    plt.grid()
    plt.ylim([0, 90])
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    #print(f"------------- Sensitivity function (S) -------------")
    #DM, GM, PM = control.disk_margins(L, omega, 1.0) # S-based (S)
    #print(f"min(DM) = {min(DM)}")
    #print(f"min(GM) = {control.db2mag(min(GM))}")
    #print(f"min(GM) = {min(GM)} dB")
    #print(f"min(PM) = {min(PM)} deg\n\n")

    #print(f"------------- Complementary sensitivity function (T) -------------")
    #DM, GM, PM = control.disk_margins(L, omega, -1.0) # T-based (T)
    #print(f"min(DM) = {min(DM)}")
    #print(f"min(GM) = {control.db2mag(min(GM))}")
    #print(f"min(GM) = {min(GM)} dB")
    #print(f"min(PM) = {min(PM)} deg\n\n")

    # Input/output loop gain
    L = control.append(P*K, K*P)
    print(f"L = {L}")

    print(f"------------- Balanced sensitivity function (S - T) -------------")
    DM, GM, PM = control.disk_margins(L, omega, 0.0) # balanced (S - T)
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {control.db2mag(min(GM))}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg\n\n")

    plt.figure(1)
    plt.subplot(3,3,3)
    plt.semilogx(omega, DM, label='$\\alpha$')
    plt.legend()
    plt.title('Disk Margin (Inputs)')
    plt.grid()
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    plt.figure(1)
    plt.subplot(3,3,6)
    plt.semilogx(omega, GM, label='$\\gamma_{m}$')
    plt.ylabel('Margin (dB)')
    plt.legend()
    plt.title('Disk-Based Gain Margin (Inputs)')
    plt.grid()
    plt.ylim([0, 40])
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    plt.figure(1)
    plt.subplot(3,3,9)
    plt.semilogx(omega, PM, label='$\\phi_{m}$')
    plt.ylabel('Margin (deg)')
    plt.legend()
    plt.title('Disk-Based Phase Margin (Inputs)')
    plt.grid()
    plt.ylim([0, 90])
    plt.tight_layout()
    plt.xlim([omega[0], omega[-1]])

    #print(f"------------- Sensitivity function (S) -------------")
    #DM, GM, PM = control.disk_margins(L, omega, 1.0) # S-based (S)
    #print(f"min(DM) = {min(DM)}")
    #print(f"min(GM) = {control.db2mag(min(GM))}")
    #print(f"min(GM) = {min(GM)} dB")
    #print(f"min(PM) = {min(PM)} deg\n\n")

    #print(f"------------- Complementary sensitivity function (T) -------------")
    #DM, GM, PM = control.disk_margins(L, omega, -1.0) # T-based (T)
    #print(f"min(DM) = {min(DM)}")
    #print(f"min(GM) = {control.db2mag(min(GM))}")
    #print(f"min(GM) = {min(GM)} dB")
    #print(f"min(PM) = {min(PM)} deg\n\n")

    if 'PYCONTROL_TEST_EXAMPLES' not in os.environ:
        plt.show()

    sys.exit(0)

    # Laplace variable
    s = control.tf('s')

    # Disk-based stability margins for example SISO loop transfer function(s)
    L = 6.25*(s + 3)*(s + 5)/(s*(s + 1)**2*(s**2 + 0.18*s + 100))
    L = 6.25/(s*(s + 1)**2*(s**2 + 0.18*s + 100))
    print(f"L = {L}\n\n")

    print(f"------------- Balanced sensitivity function (S - T) -------------")
    DM, GM, PM = control.disk_margins(L, omega, 0.0) # balanced (S - T)
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {np.db2mag(min(GM))}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg\n\n")

    print(f"------------- Sensitivity function (S) -------------")
    DM, GM, PM = control.disk_margins(L, omega, 1.0) # S-based (S)
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {np.db2mag(min(GM))}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg\n\n")

    print(f"------------- Complementary sensitivity function (T) -------------")
    DM, GM, PM = control.disk_margins(L, omega, -1.0) # T-based (T)
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {np.db2mag(min(GM))}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg\n\n")

    print(f"------------- Python control built-in -------------")
    GM_, PM_, SM_ = control.margins.stability_margins(L)[:3] # python-control default (S-based...?)
    print(f"SM_ = {SM_}")
    print(f"GM_ = {GM_} dB")
    print(f"PM_ = {PM_} deg")

    plt.figure(1)
    plt.subplot(2,3,1)
    plt.semilogx(omega, DM, label='$\\alpha$')
    plt.legend()
    plt.title('Disk Margin')
    plt.grid()

    plt.figure(1)
    plt.subplot(2,3,2)
    plt.semilogx(omega, GM, label='$\\gamma_{m}$')
    plt.ylabel('Margin (dB)')
    plt.legend()
    plt.title('Gain-Only Margin')
    plt.grid()
    plt.ylim([0, 16])

    plt.figure(1)
    plt.subplot(2,3,3)
    plt.semilogx(omega, PM, label='$\\phi_{m}$')
    plt.ylabel('Margin (deg)')
    plt.legend()
    plt.title('Phase-Only Margin')
    plt.grid()
    plt.ylim([0, 180])

    # Disk-based stability margins for example MIMO loop transfer function(s)
    P = control.tf([[[0, 1, -1],[0, 1, 1]],[[0, -1, 1],[0, 1, -1]]],
        [[[1, 0, 1],[1, 0, 1]],[[1, 0, 1],[1, 0, 1]]])
    K = control.ss([],[],[],[[-1, 0], [0, -1]])
    L = control.ss(P*K)
    print(f"L = {L}")
    DM, GM, PM = control.disk_margins(L, omega, 0.0) # balanced
    print(f"min(DM) = {min(DM)}")
    print(f"min(GM) = {min(GM)} dB")
    print(f"min(PM) = {min(PM)} deg")

    plt.figure(1)
    plt.subplot(2,3,4)
    plt.semilogx(omega, DM, label='$\\alpha$')
    plt.xlabel('Frequency (rad/s)')
    plt.legend()
    plt.grid()

    plt.figure(1)
    plt.subplot(2,3,5)
    plt.semilogx(omega, GM, label='$\\gamma_{m}$')
    plt.xlabel('Frequency (rad/s)')
    plt.ylabel('Margin (dB)')
    plt.legend()
    plt.grid()
    plt.ylim([0, 16])

    plt.figure(1)
    plt.subplot(2,3,6)
    plt.semilogx(omega, PM, label='$\\phi_{m}$')
    plt.xlabel('Frequency (rad/s)')
    plt.ylabel('Margin (deg)')
    plt.legend()
    plt.grid()
    plt.ylim([0, 180])